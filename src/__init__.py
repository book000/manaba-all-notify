import datetime
import json
import os
from enum import Enum, auto
from typing import Any, Optional, Union

import requests
from manaba import Manaba, ManabaCourse, ManabaQueryDetails, ManabaReportDetails, ManabaSurveyDetails, \
    ManabaTaskStatusFlag, \
    ManabaTaskYourStatusFlag

from src.config import Config


class Notified:
    """
    Notified
    """


class Components:
    """
    Components
    """
    notified_file_path = "notified_data.json"
    manaba: Manaba
    config: Config
    isInit: bool

    def __init__(self,
                 manaba: Manaba,
                 _config: Config):
        self.manaba = manaba
        self.config = _config
        self.isInit = not os.path.exists(self.notified_file_path)

    def discord_send_message(self,
                             channel: str,
                             content: str,
                             embed: dict[str, Any] = None) -> bool:
        """
        Send message to discord

        Args:
            channel: Discord channel id
            content: Message content
            embed: Embed

        Returns:
            bool: If successful, return True
        """
        response = requests.post("https://discord.com/api/channels/%s/messages" % (channel,),
                                 headers={
                                     "User-Agent": "manaba-all-notify (https://github.com/book000/manaba-all-notify)",
                                     "Authorization": "Bot %s" % (self.config.discord_token,),
                                     "Content-Type": "application/json",
                                     "Accept": "application/json"
                                 }, json={
                "content": content,
                "embed": embed
            })
        response.raise_for_status()

        return response.status_code == 200

    class NotifiedType(Enum):
        """
        Notified type
        """
        QUERY_TASK = auto()
        SURVEY_TASK = auto()
        REPORT_TASK = auto()

    def is_notified(self,
                    notify_type: NotifiedType,
                    notify_key: str) -> bool:
        """
        指定したキーがすでに通知済みかどうかを取得します

        Args:
            notify_type: 通知種別
            notify_key: 通知キー

        Returns:
            bool: 通知済みか
        """
        if not os.path.exists(self.notified_file_path):
            return False
        with open(self.notified_file_path) as f:
            notifieds = json.load(f)
            return notify_type.name in notifieds and notify_key in notifieds[notify_type.name]

    def set_notified(self,
                     notify_type: NotifiedType,
                     notify_key: str) -> None:
        """
        指定したキーを通知済みとしてマークします

        Args:
            notify_type: 通知種別
            notify_key: 通知キー
        """
        notifieds = {}
        if os.path.exists(self.notified_file_path):
            with open(self.notified_file_path) as f:
                notifieds = json.load(f)

        if notify_type.name in notifieds:
            notifieds[notify_type.name].append(notify_key)
        else:
            notifieds[notify_type.name] = [notify_key]

        with open(self.notified_file_path, "w") as f:
            json.dump(notifieds, f)

    class Task:
        """
        Task
        """
        course: ManabaCourse
        course_id: int
        task_id: int
        task_status: ManabaTaskStatusFlag
        your_status: ManabaTaskYourStatusFlag
        title: str
        start_time: Optional[datetime.datetime]
        end_time: Optional[datetime.datetime]

        def __init__(self, course: ManabaCourse, task: Union[ManabaQueryDetails, ManabaSurveyDetails, ManabaReportDetails]):
            self.course = course
            self.course_id = task.course_id
            self.task_status = task.status.task_status if task.status is not None else None
            self.your_status = task.status.your_status if task.status is not None and task.status.your_status is not None else None
            self.title = task.title
            self.start_time = task.reception_start_time
            self.end_time = task.reception_end_time

            if isinstance(task, ManabaQueryDetails):
                self.task_id = task.query_id

            if isinstance(task, ManabaSurveyDetails):
                self.task_id = task.survey_id

            if isinstance(task, ManabaReportDetails):
                self.task_id = task.report_id

    class TaskType(Enum):
        """
        Task type
        """
        MINI_TEST = (auto(), "query")
        SURVEY = (auto(), "survey")
        REPORT = (auto(), "report")

        def __init__(self,
                     _id: int,
                     url_param: str):
            self._id = _id
            self.url_param = url_param

    def process_task(self, task_type: TaskType, task: Task) -> None:
        """
        Process task

        Args:
            task_type: Task type
            task: Task
        """
        if os.path.exists(os.path.join("data", str(task.course_id), task_type.name.lower(), "%s.json" % task.task_id)):
            return

        if not os.path.exists(os.path.join("data", str(task.course_id), task_type.name)):
            os.makedirs(os.path.join("data", str(task.course_id), task_type.name.lower()))

        with open(os.path.join("data", str(task.course_id), task_type.name.lower(), "%s.json" % task.task_id), "w") as f:
            json.dump(task.__dict__, f)

        if self.isInit:
            return

        embed = {
            "title": "[%s] `%s` -> `%s`" % (task_type.name, task.course.name, task.title),
            "url": "%s/ct/course_%s_%s_%s" % (self.config.manaba_base_url, task.course_id, task_type.url_param, task.task_id),
            "fields": [
                {
                    "name": "Status",
                    "value": task.task_status.showing_name if task.task_status is not None else "NULL"
                },
                {
                    "name": "Your Status",
                    "value": task.your_status.showing_name if task.your_status is not None else "NULL",
                    "inline": False
                },
                {
                    "name": "Start Time",
                    "value": task.start_time.strftime("%Y-%m-%d %H:%M:%S") if task.start_time is not None else "NULL"
                },
                {
                    "name": "End Time",
                    "value": task.end_time.strftime("%Y-%m-%d %H:%M:%S") if task.end_time is not None else "NULL"
                }
            ]
        }
        result = self.discord_send_message(self.config.discord_task_channel, "", embed)
        if not result:
            print("[ERROR] Failed send message to discord")

    def crawl_query_tasks(self,
                          course: ManabaCourse) -> None:
        """
        Crawl query(mini test) tasks

        Args:
            course: Course
        """
        querys = self.manaba.get_querys(course.course_id)
        for query in querys:
            print("[INFO] Query: %s#%s" % (query.title, query.query_id))

            if self.is_notified(self.NotifiedType.QUERY_TASK, "%s-%s" % (course.course_id, query.query_id)):
                print("[INFO] -> notified")
                return

            details = self.manaba.get_query(course.course_id, query.query_id)
            task = self.Task(course, details)

            if task.task_status != ManabaTaskStatusFlag.OPENING or task.your_status != ManabaTaskYourStatusFlag.UNSUBMITTED:
                print("[INFO] -> status not open or submitted")
                return

            self.set_notified(self.NotifiedType.QUERY_TASK, "%s-%s" % (task.course_id, task.task_id))

            self.process_task(self.TaskType.MINI_TEST, task)

    def crawl_survey_tasks(self,
                           course: ManabaCourse) -> None:
        """
        Crawl survey tasks

        Args:
            course: Course
        """
        surveys = self.manaba.get_surveys(course.course_id)
        for survey in surveys:
            print("[INFO] Survey: %s#%s" % (survey.title, survey.survey_id))

            if self.is_notified(self.NotifiedType.SURVEY_TASK, "%s-%s" % (course.course_id, survey.survey_id)):
                print("[INFO] -> notified")
                return

            details = self.manaba.get_survey(course.course_id, survey.survey_id)
            task = self.Task(course, details)

            if task.task_status != ManabaTaskStatusFlag.OPENING or task.your_status != ManabaTaskYourStatusFlag.UNSUBMITTED:
                print("[INFO] -> status not open or submitted")
                return

            self.set_notified(self.NotifiedType.SURVEY_TASK, "%s-%s" % (task.course_id, task.task_id))

            self.process_task(self.TaskType.SURVEY, task)

    def crawl_report_tasks(self,
                           course: ManabaCourse) -> None:
        """
        Crawl report tasks

        Args:
            course: Course
        """
        reports = self.manaba.get_reports(course.course_id)
        for report in reports:
            print("[INFO] Report: %s#%s" % (report.title, report.report_id))

            if self.is_notified(self.NotifiedType.REPORT_TASK, "%s-%s" % (course.course_id, report.report_id)):
                print("[INFO] -> notified")
                return

            details = self.manaba.get_report(course.course_id, report.report_id)
            task = self.Task(course, details)

            if task.task_status != ManabaTaskStatusFlag.OPENING or task.your_status != ManabaTaskYourStatusFlag.UNSUBMITTED:
                print("[INFO] -> status not open or submitted")
                return

            self.set_notified(self.NotifiedType.REPORT_TASK, "%s-%s" % (task.course_id, task.task_id))

            self.process_task(self.TaskType.REPORT, task)

    def crawl_news(self,
                   course: ManabaCourse) -> None:
        """
        Crawl news

        Args:
            course: Course
        """
        news_list = self.manaba.get_news_list(course.course_id)
        for news in news_list:
            details = self.manaba.get_news(course.course_id, news.news_id)

            with open(os.path.join("data", str(course.course_id), "news", "%s-%s.json" % (news.news_id, news.last_edited_at.strftime("%Y-%m-%d_%H-%M"))),
                      "w") as f:
                json.dump(details.__dict__, f)

            embed = {
                "title": "[NEWS] `%s` -> `%s`" % (course.name, news.title),
                "url": "%s/ct/course_%s_news_%s" % (self.config.manaba_base_url, details.course_id, details.news_id),
                "fields": [
                    {
                        "name": "Author",
                        "value": details.author
                    },
                    {
                        "name": "Posted at",
                        "value": details.posted_at.strftime("%Y-%m-%d %H:%M:%S") if details.posted_at is not None else "NULL"
                    },
                    {
                        "name": "Last posted at",
                        "value": details.last_edited_at.strftime("%Y-%m-%d %H:%M:%S") if details.last_edited_at is not None else "NULL"
                    }
                ]
            }
            result = self.discord_send_message(self.config.discord_news_channel, "", embed)
            if not result:
                print("[ERROR] Failed send message to discord")


    def crawl_threads(self,
                      course: ManabaCourse) -> None:
        pass

    def crawl_contents(self,
                       course: ManabaCourse) -> None:
        pass
