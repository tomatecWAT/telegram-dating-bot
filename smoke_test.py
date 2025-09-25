"""Quick smoke test for database functions.
Run this locally to verify DB creation and basic operations without starting the bot.
"""
from database import init_db, add_user, get_user_by_telegram_id, add_like, check_match, get_matches_for_user


def run():
    init_db()
    # create two users
    add_user(telegram_id=1001, gender='male', age=30, city='CityA', target='female', bio='Hi', photo=None)
    add_user(telegram_id=1002, gender='female', age=28, city='CityB', target='male', bio='Hello', photo=None)

    u1 = get_user_by_telegram_id(1001)
    u2 = get_user_by_telegram_id(1002)
    print('User1:', u1['telegram_id'], u1['gender'], u1['age'])
    print('User2:', u2['telegram_id'], u2['gender'], u2['age'])

    add_like(1001, 1002, action='like')
    print('Match before reciprocation:', check_match(1001, 1002))
    add_like(1002, 1001, action='like')
    print('Match after reciprocation:', check_match(1001, 1002))
    print('Matches for user1:', get_matches_for_user(1001))


if __name__ == '__main__':
    run()
