"""
Main module of program.
In this module, we are getting data from configuration files
and environment variables and assign this data to the classes.
"""

import json
import os
import sys
import logging
from datetime import datetime

from core.database import Database
from core.tbot import TelegramBot


def main() -> None:
    """
    Main function of program.
    In this function, we are getting data from configuration files
     and environment variables and passing this data to the classes.
    """

    def get_data_from_json() -> dict:
        """
        Function to get configuration from JSON.
        The Configuration from JSON file has priority on Environment configuration.
        :return: Dictionary with configuration information
        """
        logger.info('Trying to get configuration from JSON file')
        try:
            with open('config.json', 'r') as config_file:
                config_dict = json.load(config_file)
                logger.info('Trying to get configuration from JSON file - Successful.')
                return config_dict
        except json.decoder.JSONDecodeError as err:
            logger.critical(
                msg=f'Configuration file has been damaged!  Error : {err}',
                stack_info=True)
            logger.critical(msg='Exiting!')
            sys.exit()

    def get_data_from_env() -> dict:
        """
        Function to get configuration from Environment.
        Using in case of VPS hosting.
        :return: Dictionary with configuration information
        """
        logger.info('Trying to get configuration from Environment')
        try:
            config_dict = {
                'TOKEN': os.environ.get('TOKEN'),
                'PROXY_TYPE': os.environ.get('PROXY_TYPE'),
                'PROXY_URL': os.environ.get('PROXY_URL'),
                'DATABASE_URL': os.environ.get('DATABASE_URL'),
                'ADMIN_PIN': os.environ.get('ADMIN_PIN')
            }
            logger.info('Trying to get configuration from Environment - Successful.')
            return config_dict
        except KeyError as err:
            logger.critical(
                msg=f'Environment configuration has been damaged!  Error : {err}',
                stack_info=True)
            logger.critical(msg='Exiting!')
            sys.exit()

    if not os.path.exists('logs'):
        os.mkdir('logs')

    logger = logging.getLogger('main.py')
    logging.basicConfig(
        filename=f'./logs/{datetime.now()}.log',
        level=logging.INFO,
        format='%(levelname)s ; %(asctime)s ; %(name)s ; %(message)s',
    )
    logger.info('Started.')

    if os.path.exists('config.json'):
        config = get_data_from_json()
    else:
        logger.warning(msg='JSON configuration file not found!')
        config = get_data_from_env()

    if config:
        database = Database(db_url=config['DATABASE_URL'])
        bot = TelegramBot(
            token=config.get('TOKEN'),
            db=database,
            proxy_type=config.get('PROXY_TYPE'),
            proxy_url=config.get('PROXY_URL'),
            adm_pin=config.get('ADMIN_PIN')
        )
        bot.run()

    else:
        logger.critical(msg='Configuration not found!')
        logger.critical(msg='Exiting!')
        sys.exit()


if __name__ == "__main__":
    main()
