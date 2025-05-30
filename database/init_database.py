import os
import sys
import logging
from database.db_operations import get_engine, init_db, get_session, setup_initial_data, create_admin_user
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    try:
        engine = get_engine()
        init_db(engine)
        session = get_session(engine)
        setup_initial_data(session)
        if len(sys.argv) > 1:
            admin_telegram_id = int(sys.argv[1])
            create_admin_user(session, admin_telegram_id)
            logger.info(f"Created admin with ID {admin_telegram_id}")
        
        logger.info("The database has been successfully initialized and filled with initial data")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()