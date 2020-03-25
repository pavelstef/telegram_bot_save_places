"""
Module of program which contains class to work with Telegram.
Based on https://github.com/eternnoir/pyTelegramBotAPI
"""

import logging
import sys
import os
from zipfile import ZipFile

import telebot as tb

import core.locationcalc as loc

LOGGER = logging.getLogger('tbot.py')


class TelegramBot:
    """ Class of Telegram  bot """

    def __init__(self, token: str, db, proxy_type: str, proxy_url: str, adm_pin: str) -> None:
        LOGGER.info(msg='Telegram bot initialisation.')
        self._token = token
        self._db = db
        self._proxy_type = proxy_type
        self._proxy_url = proxy_url
        self.__adm_pin = adm_pin
        # A dictionary that contains temporary data before adding to the database.
        self._place_content_dict = {}
        # This set contains users who are in the progress of adding a new place.
        self._user_in_progress_set = set()
        # This set contains users who ask admin mode.
        self._admin_set = set()

        if proxy_type and proxy_url:
            tb.apihelper.proxy = {proxy_type: proxy_url}

        self._bot = tb.TeleBot(self._token)

    def _main_menu(self, message) -> None:
        LOGGER.debug(msg=f'Main menu. UserID: {message.chat.id} - main menu')
        keyboard = tb.types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            tb.types.InlineKeyboardButton(text='Add new place', callback_data='add_place'),
            tb.types.InlineKeyboardButton(text='Get list of your 10 last places',
                                          callback_data='get_places'),
            tb.types.InlineKeyboardButton(text='Get your places near your current location',
                                          callback_data='get_places_location'),
            tb.types.InlineKeyboardButton(text='Delete all your places', callback_data='delete_places'),
            tb.types.InlineKeyboardButton(text='Help', callback_data='help'))
        self._bot.send_message(
            chat_id=message.chat.id,
            text='What do you want to do?',
            reply_markup=keyboard
        )

    def _help_massage(self, message) -> None:
        LOGGER.debug(msg=f'UserID: {message.chat.id} - help message')
        help_message_text = """
        I am a bot that will help you save interesting places.
I can:
+ Save information about some place for you.
+ Provide you list of your 10 last places.
+ Provide you list of your 10 places near your current location.
"""
        self._bot.send_message(chat_id=message.chat.id, text=help_message_text)
        self._main_menu(message)

    def _send_places(self, message, places) -> None:
        LOGGER.debug(msg=f'UserID: {message.chat.id} - Send places')
        try:
            if places:
                self._bot.send_message(chat_id=message.chat.id, text='Your places:')
                for num, place in enumerate(places):
                    if place['photo'] is not None:
                        self._bot.send_photo(
                            chat_id=message.chat.id,
                            photo=place['photo'],
                            caption=f"#{num + 1} - {place['description']}"
                        )
                        self._bot.send_location(
                            message.chat.id, place['lat'], place['long']
                        )
                    else:
                        self._bot.send_message(
                            chat_id=message.chat.id,
                            text=f"#{num + 1} - {place['description']}"
                        )
                        self._bot.send_location(
                            message.chat.id, place['lat'], place['long']
                        )
            else:
                self._bot.send_message(
                    chat_id=message.chat.id, text='Your places were not found.'
                )
            self._main_menu(message)
        except tb.apihelper.ApiException as err:
            LOGGER.error(msg=f'UserID: {message.chat.id}. API Exception: {err}')
            self._main_menu(message)

    def _list_last_places(self, message) -> None:
        LOGGER.debug(msg=f'UserID: {message.chat.id} - list last places')
        places = self._db.get_last_places(user_id=message.chat.id)
        self._send_places(message, places)

    def _ask_location(self, message) -> None:
        LOGGER.debug(msg=f'UserID: {message.chat.id} - ask location')
        keyboard = tb.types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            tb.types.InlineKeyboardButton(text='Cancel', callback_data='cancel')
        )
        self._bot.send_message(
            chat_id=message.chat.id,
            text='Please, send your location',
            reply_markup=keyboard
        )

    def _places_near_location(self, message) -> None:
        LOGGER.debug(msg=f'UserID: {message.chat.id} - places near location.')
        area = loc.get_area_coord(
            lat=message.location.latitude,
            long=message.location.longitude,
            distance=500
        )
        places = self._db.get_near_places(user_id=message.chat.id, area=area)
        self._send_places(message, places)

    def _delete_users_data(self, message) -> None:
        LOGGER.debug(msg=f'UserID: {message.chat.id} - delete user\'s data')
        self._db.delete_places(user_id=message.chat.id)
        self._bot.send_message(
            chat_id=message.chat.id,
            text='All your places have been deleted!'
        )
        self._main_menu(message)

    def _add_new_place_start(self, message) -> None:
        LOGGER.debug(msg=f'UserID: {message.chat.id} - adding new place start')
        self._place_content_dict[message.chat.id] = {}
        self._user_in_progress_set.add(message.chat.id)
        add_location_text = """
In order to add a new place you need to add the following parameters:
+ location (required)
+ description (required, less than 250 symbols)
+ photo (optional)
"""
        self._bot.send_message(chat_id=message.chat.id, text=add_location_text)
        self._add_new_place_menu(message)

    def _add_new_place_menu(self, message) -> None:
        LOGGER.debug(msg=f'UserID: {message.chat.id} - adding new place menu')
        keyboard = tb.types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            tb.types.InlineKeyboardButton(text='Add location', callback_data='location'),
            tb.types.InlineKeyboardButton(text='Add description', callback_data='description'),
            tb.types.InlineKeyboardButton(text='Add photo', callback_data='photo'),
            tb.types.InlineKeyboardButton(text='Cancel', callback_data='cancel')
        )
        if 'lat' in self._place_content_dict[message.chat.id].keys(
        ) and 'description' in self._place_content_dict[message.chat.id].keys():
            keyboard.add(tb.types.InlineKeyboardButton(text='Save', callback_data='save'))
        self._bot.send_message(
            chat_id=message.chat.id,
            text='Please, choose action.',
            reply_markup=keyboard
        )

    def _add_new_place_location(self, message) -> None:
        LOGGER.debug(msg=f'UserID: {message.chat.id} - adding new place location')
        self._place_content_dict[message.chat.id].update({
            'lat': message.location.latitude,
            'long': message.location.longitude
        })
        self._bot.send_message(
            chat_id=message.chat.id,
            text='Location received.')
        self._add_new_place_menu(message)

    def _add_new_place_description(self, message) -> None:
        LOGGER.debug(msg=f'UserID: {message.chat.id} - adding new place description')
        self._place_content_dict[message.chat.id].update({
            'description': f"'{message.text[:250]}'"
        })
        self._bot.send_message(
            chat_id=message.chat.id,
            text='Description received.'
        )
        self._add_new_place_menu(message)

    def _add_new_place_photo(self, message) -> None:
        LOGGER.debug(msg=f'UserID: {message.chat.id} - adding new place photo')

        # message.photo[0] = small size 'height': 320, 'width': 180
        photo_id_small = message.photo[0].file_id
        photo_info = self._bot.get_file(photo_id_small)
        photo_binary = self._bot.download_file(photo_info.file_path)

        self._place_content_dict[message.chat.id].update({'photo': photo_binary})
        self._bot.send_message(chat_id=message.chat.id, text='Photo received.')
        self._add_new_place_menu(message)

    def _add_new_place_save(self, message) -> None:
        LOGGER.debug(msg=f'UserID: {message.chat.id} - adding new place save')
        self._db.create_new_place(
            user_id=message.chat.id,
            content=self._place_content_dict[message.chat.id]
        )
        self._bot.send_message(
            chat_id=message.chat.id,
            text='Your place has been saved!'
        )
        self._place_content_dict.pop(message.chat.id)
        self._user_in_progress_set.remove(message.chat.id)
        self._main_menu(message)

    def _admin_menu(self, message) -> None:
        LOGGER.warning(msg=f'UserID: {message.chat.id} - admin menu')
        keyboard = tb.types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            tb.types.InlineKeyboardButton(text='Get logs', callback_data='logs'),
            tb.types.InlineKeyboardButton(text='Exit', callback_data='exit')
        )
        self._bot.send_message(
            chat_id=message.chat.id,
            text='Admin action.',
            reply_markup=keyboard
        )

    def _admin_get_logs(self, message):
        with ZipFile('logs.zip', 'w') as zip_file:
            for dir_name, _, file_list in os.walk('../logs'):
                for file in file_list:
                    file_patch = os.path.join(dir_name, file)
                    zip_file.write(file_patch)
        if os.path.exists('logs.zip'):
            with open('logs.zip', 'rb') as file:
                self._bot.send_document(message.chat.id, file)
        self._admin_menu(message)

    def run(self) -> None:
        """
        The main method for the bot.
        The method contains bot's work logic
        """
        LOGGER.info(msg='Bot starting.')

        def user_in_set(user_id, some_set) -> bool:
            if user_id in some_set:
                return True
            return False

        @self._bot.callback_query_handler(func=lambda x: True)
        def callback_handler(callback_query) -> None:
            """ This method provide interaction menu for each cases """
            chat_id = callback_query.message.chat.id
            text_question = callback_query.message.text
            text_answer = callback_query.data
            LOGGER.debug(
                msg=f'Callback received. UserID: {chat_id}, text question: {text_question},'
                f' text answer: {text_answer}'
            )
            if text_question == 'What do you want to do?':
                if text_answer == 'add_place':
                    self._add_new_place_start(callback_query.message)
                elif text_answer == 'get_places':
                    self._list_last_places(callback_query.message)
                elif text_answer == 'get_places_location':
                    self._ask_location(callback_query.message)
                elif text_answer == 'delete_places':
                    self._delete_users_data(callback_query.message)
                elif text_answer == 'help':
                    self._help_massage(callback_query.message)

            elif text_question == 'Please, choose action.':
                if text_answer == 'location' and \
                        user_in_set(callback_query.message.chat.id, self._user_in_progress_set):
                    self._bot.send_message(
                        chat_id=callback_query.message.chat.id,
                        text='Please, send place location.'
                    )
                elif text_answer == 'description' and \
                        user_in_set(callback_query.message.chat.id, self._user_in_progress_set):
                    self._bot.send_message(
                        chat_id=callback_query.message.chat.id,
                        text='Please, send place description (less than 250 symbols).'
                    )
                elif text_answer == 'photo' and \
                        user_in_set(callback_query.message.chat.id, self._user_in_progress_set):
                    self._bot.send_message(
                        chat_id=callback_query.message.chat.id,
                        text='Please, send place photo.'
                    )
                elif text_answer == 'save' and \
                        user_in_set(callback_query.message.chat.id, self._user_in_progress_set):
                    self._add_new_place_save(callback_query.message)
                elif text_answer == 'cancel' and \
                        user_in_set(callback_query.message.chat.id, self._user_in_progress_set):
                    self._place_content_dict.pop(callback_query.message.chat.id)
                    self._user_in_progress_set.remove(callback_query.message.chat.id)
                    self._main_menu(callback_query.message)

            elif text_question == 'Admin action.':
                if text_answer == 'logs':
                    self._admin_get_logs(callback_query.message)
                elif text_answer == 'exit':
                    self._admin_set.remove(callback_query.message.chat.id)
                    self._main_menu(callback_query.message)

            else:
                self._main_menu(callback_query.message)

        @self._bot.message_handler(commands=['start'])
        def create_new_user(message) -> None:
            LOGGER.debug(msg=f'UserID: {message.chat.id} - start point')
            self._db.create_user(user_id=message.chat.id)
            self._bot.send_message(chat_id=message.chat.id, text='Welcome!')
            self._help_massage(message)

        @self._bot.message_handler(commands=['admin'])
        def call_admin_menu(message) -> None:
            LOGGER.debug(msg=f'UserID: {message.chat.id} - admin command got')
            self._admin_set.add(message.chat.id)
            self._bot.send_message(chat_id=message.chat.id, text='#>')

        @self._bot.message_handler(
            func=lambda message: user_in_set(message.chat.id, self._user_in_progress_set),
            content_types=['location'])
        def call_add_place_location(message) -> None:
            LOGGER.debug(msg=f'UserID: {message.chat.id} - text: {message.text}')
            self._add_new_place_location(message)

        @self._bot.message_handler(
            func=lambda message: user_in_set(message.chat.id, self._user_in_progress_set),
            content_types=['text'])
        def call_add_place_description(message) -> None:
            LOGGER.debug(msg=f'UserID: {message.chat.id} - text: {message.text}')
            self._add_new_place_description(message)

        @self._bot.message_handler(
            func=lambda message: user_in_set(message.chat.id, self._user_in_progress_set),
            content_types=['photo'])
        def call_add_place_photo(message) -> None:
            LOGGER.debug(msg=f'UserID: {message.chat.id} - text: {message.text}')
            self._add_new_place_photo(message)

        @self._bot.message_handler(
            func=lambda message: user_in_set(message.chat.id, self._admin_set),
            content_types=['text'])
        def check_admin_pin(message) -> None:
            LOGGER.debug(msg=f'UserID: {message.chat.id} - text: {message.text}')
            if message.text == self.__adm_pin:
                self._admin_menu(message)
            else:
                LOGGER.warning(
                    msg=f'UserID: {message.chat.id} - admin login unsuccessful!')
                self._admin_set.remove(message.chat.id)
                self._main_menu(message)

        @self._bot.message_handler(content_types=['location'])
        def call_location_method(message) -> None:
            LOGGER.debug(msg=f'UserID: {message.chat.id} - text: {message.text}')
            self._bot.send_message(
                chat_id=message.chat.id,
                text='Location received.'
            )
            self._places_near_location(message)

        @self._bot.message_handler()
        def any_massage(message) -> None:
            LOGGER.debug(msg=f'UserID: {message.chat.id} - text: {message.text}')
            self._main_menu(message)

        try:
            LOGGER.info(msg='Polling starting')
            self._bot.remove_webhook()
            self._bot.polling(none_stop=True, timeout=10)
        except Exception as err:
            LOGGER.critical(msg=f'Problem with Telegram bot. Error: {err}')
            LOGGER.critical(msg='Exiting!')
            self._db.close()
            sys.exit()
