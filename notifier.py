import asyncio
import os
import datetime
import logging

import slack
import requests_oauthlib
from oauthlib import oauth2

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('notifier')

REGISTER_INTERVAL = int(os.environ['REGISTER_INTERVAL'])
PENDING_INTERVAL = int(os.environ['PENDING_INTERVAL'])

KEYCLOAK_URL = os.environ['KEYCLOAK_URL']
KEYCLOAK_REALM = os.environ['KEYCLOAK_REALM']
KEYCLOAK_ROLE = os.environ['KEYCLOAK_ROLE']
KEYCLOAK_CLIENT_ID = os.environ['KEYCLOAK_CLIENT_ID']
KEYCLOAK_CLIENT_SECRET = os.environ['KEYCLOAK_CLIENT_SECRET']
KEYCLOAK_TOKEN_URL = f'{KEYCLOAK_URL.strip("/")}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token'
KEYCLOAK_ROLE_USERS = f'{KEYCLOAK_URL.strip("/")}/admin/realms/{KEYCLOAK_REALM}/roles/{KEYCLOAK_ROLE}/users'
KEYCLOAK_EVENTS = f'{KEYCLOAK_URL.strip("/")}/admin/realms/{KEYCLOAK_REALM}/events'

SLACK_CHANNEL = os.environ['SLACK_CHANNEL']
SLACK_API_TOKEN = os.environ['SLACK_API_TOKEN']

extra = {
    'client_id': KEYCLOAK_CLIENT_ID,
    'client_secret': KEYCLOAK_CLIENT_SECRET,
}

token = {}

def token_updater(new_token):
    token = new_token

client = oauth2.BackendApplicationClient(KEYCLOAK_CLIENT_ID)
session = requests_oauthlib.OAuth2Session(
    client=client,
    token=token,
    auto_refresh_kwargs=extra,
    auto_refresh_url=KEYCLOAK_TOKEN_URL,
    token_updater=token_updater)

token = session.fetch_token(KEYCLOAK_TOKEN_URL, client_secret=KEYCLOAK_CLIENT_SECRET)

async def keycloak_new_users(session):
    try:
        response = session.get(KEYCLOAK_EVENTS, params={'type': 'REGISTER'})
    except Exception as e:
        logger.error(f'Error querying keycloak {str(e)}')

        return None

    logger.info(f'Status code {response.status_code}')

    if response.status_code != 200:
        return None

    data = response.json()

    logger.debug(f'Response {data}')

    users = [
        'New users',
    ]

    for x in data:
        time = datetime.datetime.fromtimestamp(x['time']/1000)

        since = (datetime.datetime.now()-time).total_seconds()

        details = x['details']

        users.append(f'- {details["username"]} {details["email"]} (since {round(since/3600.0, 2)} hrs)')

    logger.info(f'Found {len(users)-1} new users')

    if len(users) == 1:
        return None

    return '\n'.join(users)

async def periodic_new_users():
    client = oauth2.BackendApplicationClient(KEYCLOAK_CLIENT_ID)
    session = requests_oauthlib.OAuth2Session(
        client=client,
        token=token,
        auto_refresh_kwargs=extra,
        auto_refresh_url=KEYCLOAK_TOKEN_URL,
        token_updater=token_updater)

    slack_client = slack.WebClient(token=SLACK_API_TOKEN)

    while True:
        users = await keycloak_new_users(session)

        if users is not None:
            slack_client.chat_postMessage(channel=SLACK_CHANNEL, text=users)

        await asyncio.sleep(REGISTER_INTERVAL)

async def keycloak_role_users(session):
    try:
        response = session.get(KEYCLOAK_ROLE_USERS)
    except Exception as e:
        logger.error(f'Error querying keycloak {str(e)}')

        return None

    if response.status_code != 200:
        return None

    data = response.json()

    logger.debug(f'Response {data}')

    users = [
        'Users pending approval',
    ]

    for x in data:
        time = datetime.datetime.fromtimestamp(x['createdTimestamp']/1000)

        since = (datetime.datetime.now()-time).total_seconds()

        users.append(f'- {x["username"]} {x["email"]} (since {round(since/3600.0, 2)} hrs)')

    logger.info(f'Found {len(users)-1} users waiting approval')

    if len(users) == 1:
        return None

    return '\n'.join(users)

async def periodic_role_users():
    client = oauth2.BackendApplicationClient(KEYCLOAK_CLIENT_ID)
    session = requests_oauthlib.OAuth2Session(
        client=client,
        token=token,
        auto_refresh_kwargs=extra,
        auto_refresh_url=KEYCLOAK_TOKEN_URL,
        token_updater=token_updater)

    slack_client = slack.WebClient(token=SLACK_API_TOKEN)

    while True:
        users = await keycloak_role_users(session)

        if users is not None:
            slack_client.chat_postMessage(channel=SLACK_CHANNEL, text=users)

        await asyncio.sleep(PENDING_INTERVAL)

async def main():
    await asyncio.gather(
        periodic_new_users(),
        periodic_role_users())

asyncio.run(main())
