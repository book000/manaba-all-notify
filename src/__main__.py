import os

from manaba import Manaba

from src import Components
from src.config import load_config


def main() -> None:
    """
    Main
    """
    manaba = Manaba(base_url=config.manaba_base_url)
    manaba.login(config.manaba_username, config.manaba_password)
    if not os.path.exists("data"):
        os.mkdir("data")

    components = Components(manaba, config)

    courses = manaba.get_courses()
    for course in courses:
        print("[INFO] Course: %s#%s" % (course.name, course.course_id))
        if not os.path.exists(os.path.join("data", str(course.course_id))):
            os.mkdir(os.path.join("data", str(course.course_id)))

        components.crawl_query_tasks(course)
        components.crawl_survey_tasks(course)
        components.crawl_report_tasks(course)
        components.crawl_news(course)
        components.crawl_threads(course)
        components.crawl_contents(course)

    print(config)
    print(config.discord_token)


if __name__ == "__main__":
    config = load_config("config.json")
    if config is None:
        print("[ERROR] Failed to load config")
        exit(1)
    main()
