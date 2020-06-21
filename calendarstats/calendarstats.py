import collections
import copy
import logging
import time

from icalendar import Calendar, Event
# from datetime import datetime
# from datetime import date
import datetime
from pytz import UTC # timezone

from utils import auto_str

LOG = logging.getLogger(__name__)

@auto_str
class CalendarEvent:
    def __init__(self, summary, start_time, end_time):
        self.summary = summary
        self.start_time = start_time
        self.end_time = end_time
        self.length = self.calculate_length()

    def get_year(self):
        return self.start_time.year

    def get_week(self):
        return self.start_time.isocalendar()[1]

    def spans_more_days(self):
        return self.end_time.day - self.start_time.day

    def calculate_length(self):
        time_delta = (self.end_time - self.start_time)
        total_seconds = time_delta.total_seconds()
        return total_seconds / 60

    def __repr__(self):
        return self.__str__()


@auto_str
class Week:
    def __init__(self, start_date, end_date, week_no):
        self.start_date = convert_to_datetime(start_date)
        self.end_date = convert_to_datetime(end_date, end_of_day=True)
        self.week_no = week_no

    def __repr__(self):
        return self.__str__()

    def __lt__(self, other):
        return self.start_date < other.start_date


class AllWeeks:
    def __init__(self, years):
        self.weeks_by_year = {}
        for y in years:
            weeks = AllWeeks.find_weeks_in_year(y)
            self.weeks_by_year[y] = AllWeeks.convert_to_week_objs(weeks, y)

    def get_week_obj_of_event(self, event):
        year = event.get_year()
        week = event.get_week()
        try:
            week_obj = self.weeks_by_year[year][week - 1]
        except IndexError:
            print("IndexError for year: " + str(year))
            # Last week of 2020
            # 2021.01.01 --> Week of 53 in 2020
            # Week 53, 2020	December 28, 2020	January 3, 2021
            # Week 01, 2021	January 4, 2021	January 10, 2021
            if week > 52:
                # TODO why this may happen?
                week = 52
            week_obj = self.weeks_by_year[year - 1][week - 1]

        if event.spans_more_days():
            print("Ignoring multi day event: " + str(event))
            return None
        # double check start date
        if week_obj.start_date <= event.start_time and week_obj.end_date > event.end_time:
            # print("OK")
            pass
        else:
            print("NOT OK")
        return week_obj

    @staticmethod
    def convert_to_week_objs(week_list, year):
        result = []
        for i, date in enumerate(week_list):
            if i + 1 < len(week_list):
                week_id = str(year) + "-" + str(i + 1)
                result.append(Week(date, week_list[i + 1] - datetime.timedelta(1), week_id))
        return result

    @staticmethod
    def find_weeks_in_year(year):
        # Original implementation is from:
        # https://www.daniweb.com/programming/software-development/threads/67566/get-week-list-of-an-year
        """ will return all the week from selected year """
        import datetime
        WEEK = {'MONDAY': 0, 'TUESDAY': 1, 'WEDNESDAY': 2, 'THURSDAY': 3, 'FRIDAY': 4, 'SATURDAY': 5, 'SUNDAY': 6}
        MONTH = {'JANUARY': 1, 'FEBRUARY': 2, 'MARCH': 3, 'APRIL': 4, 'MAY': 5, 'JUNE': 6, 'JULY': 7, 'AUGUST': 8,
                 'SEPTEMBER': 9, 'OCTOBER': 10, 'NOVEMBER': 11, 'DECEMBER': 12}
        year = int(year)
        month = MONTH['DECEMBER']
        day = WEEK['MONDAY']
        # dt = datetime.date(year, month, 1)
        dt = datetime.date(year - 1, month, 31)
        dt = AllWeeks._find_next_monday(day, dt)

        monday_from_last_year = False
        if dt.year != year:
            monday_from_last_year = True

        weeks = []
        while True:
            weeks.append(dt)
            prev_dt = dt
            dt = dt + datetime.timedelta(days=7)
            if monday_from_last_year:
                monday_from_last_year = False
                continue

            if prev_dt.month == 12 and dt.month != 12:
                prev_dt = dt + datetime.timedelta(-7)
                dt = AllWeeks._find_next_monday(day, prev_dt, force=True)
                weeks.append(dt)
                break
        return weeks

    @staticmethod
    def _find_next_monday(day, dt, force=False):
        if force:
            if dt.weekday() == 0:
                dt = dt + datetime.timedelta(days=7)
            while dt.weekday() != day:
                dt = dt + datetime.timedelta(days=1)

        if dt.weekday() > 0:
            while dt.weekday() != day:
                dt = dt + datetime.timedelta(days=1)
        return dt


def get_all_years(events):
    years = set()
    for ev in events:
        years.add(ev.get_year())

    return years


def convert_to_datetime(date, start_of_day=False, end_of_day=False):
    if start_of_day and end_of_day:
        raise ValueError("Either start_of_day or end_of_day should be used but not both!")
    if not start_of_day and not end_of_day:
        start_of_day = True

    if start_of_day:
        return datetime.datetime(date.year, date.month, date.day, tzinfo=UTC)
    elif end_of_day:
        return datetime.datetime(date.year, date.month, date.day, 23, 59, 59, tzinfo=UTC)


class CalendarStats:
    def __init__(self):
        pass

    def start(self):
        events = self.parse_events()
        sorted_events = sorted(events, key=lambda x: x.start_time)

        years = get_all_years(sorted_events)
        all_weeks = AllWeeks(years)

        events_by_week = {}
        for ev in events:
            week_obj = all_weeks.get_week_obj_of_event(ev)
            if not week_obj:
                continue

            if week_obj not in events_by_week:
                events_by_week[week_obj] = []
            events_by_week[week_obj].append(ev)

        ordered_dict = collections.OrderedDict(sorted(events_by_week.items()))

        print("Listing of Length of meetings per week...")
        for week_obj, ev_list in ordered_dict.items():
            # print("Week: " + week_obj.week_no + ": " + str(ev_list))
            sum_length = 0
            for ev in ev_list:
                sum_length += ev.length
            sum_length /= 60
            print(week_obj.week_no + ": " + str(sum_length))

    def parse_events(self):
        cal_file = open('/Users/szilardnemeth/Downloads/snemeth@cloudera.com.ics', 'rb')
        gcal = Calendar.from_ical(cal_file.read())
        events = []
        for component in gcal.walk():
            if component.name == "VEVENT":
                summary = component.get('summary')
                start_date = component.get('dtstart').dt
                end_date = component.get('dtend').dt
                dtstamp = component.get('dtstamp').dt

                if type(start_date) is datetime.date:
                    # print("Found date instance: " + str(start_date))
                    start_date = convert_to_datetime(start_date)

                if type(end_date) is datetime.date:
                    # print("Found date instance: " + str(end_date))
                    end_date = convert_to_datetime(end_date)
                events.append(CalendarEvent(summary, start_date, end_date))
        cal_file.close()
        return events


if __name__ == '__main__':
    start_time = time.time()

    # Parse args
    # args = Setup.parse_args()
    cal_stats = CalendarStats()

    # Initialize logging
    # verbose = True if args.verbose else False
    # Setup.init_logger(cal_stats.log_dir, console_debug=verbose)

    cal_stats.start()
    end_time = time.time()
    LOG.info("Execution of script took %d seconds", end_time - start_time)

