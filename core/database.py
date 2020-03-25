"""
Module of program which contains class to work with PostgreSQL Database.
"""

import logging

import psycopg2

LOGGER = logging.getLogger('database.py')


class Database:
    """  class to work with PostgreSQL Database """

    def __init__(self, db_url: str) -> None:
        LOGGER.info(msg='Database class initialisation.')
        try:
            self._conn = psycopg2.connect(db_url, sslmode='require')
            self._cursor = self._conn.cursor()
            LOGGER.info(msg='The connection to DB has been created.')
        except Exception as err:
            LOGGER.error(msg=f'Problem connecting to database. Error: {err}')
        else:
            try:
                self._cursor.execute(
                    """
                    create table if not exists users (
                        user_id bigint not null primary key,
                        created_at timestamp default now()
                    )
                    """
                )
                self._cursor.execute(
                    """
                    create table if not exists places (
                        user_id bigint not null,
                        lat  numeric not null,
                        long numeric not null,
                        place_description varchar(255),
                        photo bytea,
                        created_at timestamp default now(),
                        foreign key (user_id) references users(user_id)
                    );
                    """
                )
                self._cursor.execute(
                    'create index if not exists idx_places on places(user_id, created_at)'
                )
                self._conn.commit()
                LOGGER.info(msg='The tables have been created.')
            except Exception as err:
                self._conn.rollback()
                LOGGER.error(msg=f'Problem connecting to database. Error: {err}')

    def create_user(self, user_id: str) -> None:
        """ Creating new user in DB """
        LOGGER.debug(msg=f'Creating user. UserID: {user_id}.')
        try:
            self._cursor.execute(
                f'insert into users (user_id) values ({user_id})'
            )
            self._conn.commit()
            LOGGER.debug(msg=f'UserID: {user_id} has bean created.')
        except Exception as err:
            self._conn.rollback()
            LOGGER.error(msg=f'Problem creating user. UserID: {user_id}. Error: {err}')

    def get_last_places(self, user_id: str) -> dict:
        """ Getting last 10 places """
        LOGGER.debug(msg=f'Getting las 10 places. UserID: {user_id}.')
        try:
            self._cursor.execute(
                f"""
                select lat, long, place_description, photo
                    from places
                    where user_id = {user_id}
                    order by created_at desc
                    limit 10
                """
            )
            result = self._cursor.fetchall()
            for i in range(len(result)):
                result[i] = {
                    'lat': str(result[i][0]),
                    'long': str(result[i][1]),
                    'description': result[i][2],
                    'photo': result[i][3]
                }
            LOGGER.debug(msg=f'Getting las 10 places. UserID: {user_id} - Success.')
            return result
        except Exception as err:
            self._conn.rollback()
            LOGGER.error(msg=f'Problem getting las 10 places. UserID: {user_id}. Error: {err}')

    def delete_places(self, user_id: str) -> None:
        """ Deleting all places of user """
        LOGGER.debug(msg=f'Deleting all places of user. UserID: {user_id}.')
        try:
            self._cursor.execute(
                f'delete from places where user_id = {user_id}'
            )
            self._conn.commit()
            LOGGER.debug(msg=f'All places of UserID: {user_id} have bean deleted.')
        except Exception as err:
            self._conn.rollback()
            LOGGER.error(msg=f'Problem with deleting user\'s places. UserID: {user_id}. Error: {err}')

    def get_near_places(self, user_id: str, area: list) -> dict:
        """ Getting all places near location (places which wre located into some area) """
        LOGGER.debug(msg=f'Getting places near location. UserID: {user_id}.')
        try:
            self._cursor.execute(
                f"""
                select lat, long, place_description, photo
                    from places
                    where user_id = {user_id}
                        and (lat between {area[0]} and {area[2]})
                        and (long between {area[1]} and {area[3]})
                    order by created_at desc
                    limit 10;
                """
            )
            result = self._cursor.fetchall()
            for i in range(len(result)):
                result[i] = {
                    'lat': str(result[i][0]),
                    'long': str(result[i][1]),
                    'description': result[i][2],
                    'photo': result[i][3]
                }
            LOGGER.debug(msg=f'Getting places near location. UserID: {user_id} - Success.')
            return result
        except Exception as err:
            self._conn.rollback()
            LOGGER.error(msg=f'Problem getting places near location. UserID: {user_id}. Error: {err}')

    def create_new_place(self, user_id: str, content: dict) -> None:
        """ Creating a new place in DB """
        LOGGER.debug(msg=f'Creating new place. UserID: {user_id}.')
        try:
            if 'photo' in content.keys():
                self._cursor.execute(
                    f"""
                    insert into places
                    (user_id, lat, long, place_description, photo)
                    values
                    (%(id)s, %(lat)s, %(long)s, %(desc)s, %(photo)s)
                    """,
                    {'id': user_id, 'lat': content['lat'], 'long': content['long'],  'desc': content['description'],
                     'photo': psycopg2.Binary(content['photo'])}
                )
                self._conn.commit()
            else:
                self._cursor.execute(
                    """
                    insert into places
                    (user_id, lat, long, place_description)
                    values
                    (%(id)s, %(lat)s, %(long)s, %(desc)s)
                    """,
                    {'id': user_id, 'lat': content['lat'], 'long': content['long'],  'desc': content['description']}
                )
                self._conn.commit()
                LOGGER.debug(msg=f'Creating new place. UserID: {user_id} - Success.')
        except Exception as err:
            self._conn.rollback()
            LOGGER.error(msg=f'Problem creating new place. UserID: {user_id}. Error: {err}')

    def close(self) -> None:
        """ Closing connection to DB """
        try:
            self._conn.close()
            LOGGER.info(msg=f'The connection to DB has been closed.')
        except Exception as err:
            LOGGER.error(msg=f'Problem with closing DB connection. Error: {err}')
