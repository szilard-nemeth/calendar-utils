import collections
import logging
import time
from os.path import expanduser

from icalendar import Calendar
import datetime

from pythoncommons.string_utils import auto_str
from pytz import UTC # timezone
from config import Config
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

    def is_within_last_week_of_year(self):
        year = self.get_year()

        from_date = datetime.datetime(year, 12, 25, 00, 00, 00, tzinfo=UTC)
        to_date = datetime.datetime(year, 12, 31, 23, 59, 59, tzinfo=UTC)
        return from_date <= self.start_time and self.end_time <= to_date

    def is_within_first_week_of_year(self):
        year = self.get_year()

        from_date = datetime.datetime(year, 1, 1, 00, 00, 00, tzinfo=UTC)
        to_date = datetime.datetime(year, 1, 7, 23, 59, 59, tzinfo=UTC)
        return from_date <= self.start_time and self.end_time <= to_date

    def calculate_length(self):
        time_delta = (self.end_time - self.start_time)
        total_seconds = time_delta.total_seconds()
        return total_seconds / 60

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.start_time == other.start_time and \
               self.end_time == other.end_time and \
               self.summary == other.summary


@auto_str
class Week:
    def __init__(self, start_date, end_date, week_no, year):
        self.start_date = convert_to_datetime(start_date)
        self.end_date = convert_to_datetime(end_date, end_of_day=True)
        self.week_no = week_no
        self.year = year

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
            LOG.error("IndexError for year: %d", year)
            # Last week of 2020
            # 2021.01.01 --> Week of 53 in 2020
            # Week 53, 2020	December 28, 2020	January 3, 2021
            # Week 01, 2021	January 4, 2021	January 10, 2021
            if week > 52:
                # TODO why this may happen?
                week = 52
            week_obj = self.weeks_by_year[year - 1][week - 1]

        if event.spans_more_days():
            LOG.info("Ignoring multi day event: %s", event)
            return None
        # double check start date
        if self._check_if_event_date_within_week_range(event, week_obj):
            # print("OK")
            pass
        else:
            if event.is_within_last_week_of_year():
                # For dates of year-12-31, sometimes week number can be 1.
                # Let's check the last week of the year then instead of checking 1st week as per index.
                # TODO add warning log here
                week_obj = self.weeks_by_year[year][-1]
                self._check_if_event_date_within_week_range(event, week_obj, raise_error=True)
            elif event.is_within_first_week_of_year():
                # For dates of year-01-01 and onwards, sometimes week can be stored for the previous year.
                # Let's try to look it up from the last week of previous year.
                # TODO add warning log here
                week_obj = self.weeks_by_year[year - 1][-1]
                self._check_if_event_date_within_week_range(event, week_obj, raise_error=True)
            else:
                raise Exception("Event is not in range of week. Event: {}, week: {}".format(event, week_obj))
        return week_obj

    @staticmethod
    def _check_if_event_date_within_week_range(event, week_obj, raise_error=False):
        res = week_obj.start_date <= event.start_time and week_obj.end_date > event.end_time
        if not res and raise_error:
            raise Exception("Event is not in range of week. Event: {}, week: {}".format(event, week_obj))
        return res

    @staticmethod
    def convert_to_week_objs(week_list, year):
        result = []
        for i, date in enumerate(week_list):
            if i + 1 < len(week_list):
                week_id = str(year) + "-" + str(i + 1)
                result.append(Week(date, week_list[i + 1] - datetime.timedelta(1), week_id, year))
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
        month = MONTH['JANUARY']
        day = WEEK['MONDAY']
        thursday = WEEK['THURSDAY']

        # https://www.epochconverter.com/weeknumbers
        # Week number according to the ISO-8601 standard, weeks starting on Monday.
        # The first week of the year is the week that contains that year's first Thursday
        # (='First 4-day week'). ISO representation: 2020-W25
        dt = datetime.date(year, month, 1)
        if dt.weekday() >= thursday:
            dt = AllWeeks._find_next_monday(day, dt)
            monday_from_last_year = False
        else:
            dt = AllWeeks._find_prev_monday(day, dt)
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

    @staticmethod
    def _find_prev_monday(day, dt):
        if dt.weekday() > 0:
            while dt.weekday() != day:
                dt = dt - datetime.timedelta(days=1)
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
    def __init__(self, conf):
        self.conf = conf
        self.file = self.conf.args.file
        self.exceptions = self.conf.args.event_exceptions
        self.filter_year = list(map(int, self.conf.args.filter_year))

    def start(self):
        events = self.parse_events()

        if self.exceptions:
            events = self.filter_events_by_exceptions(events)

        if self.filter_year:
            LOG.info("Filtering events, only with years: %s", self.filter_year)
            events = filter(lambda x: x.get_year() in self.filter_year, events)

        sorted_events = sorted(events, key=lambda x: x.start_time)

        LOG.info("Printing unique event names (A-Z)...")
        unique_event_names = set(map(lambda x: x.summary, sorted_events))
        sorted_unique_event_names = sorted(list(unique_event_names))
        for event_name in sorted_unique_event_names:
            LOG.info(event_name)

        years = get_all_years(sorted_events)
        all_weeks = AllWeeks(years)
        events_by_week = self.get_events_by_week(all_weeks, sorted_events)

        LOG.info("Listing of summarized length of meetings per week...")

        yearly_sum = dict([(y, 0) for y in years])
        now = datetime.datetime.now(tz=UTC)
        for week_obj, ev_list in events_by_week.items():
            sum_length_in_mins = 0
            for ev in ev_list:
                sum_length_in_mins += ev.length
            sum_length_in_hours = sum_length_in_mins / 60
            LOG.info("%s: %d", week_obj.week_no, sum_length_in_hours)

            # Only add weeks to yearly sum that precedes (or same as) current week
            if week_obj.start_date.year != now.year or \
                    (week_obj.start_date.year == now.year and (week_obj.end_date < now or week_obj.start_date < now)):
                # LOG.info("Added week to yearly sum: %s", week_obj)
                yearly_sum[week_obj.year] += sum_length_in_hours

        for year, sum in yearly_sum.items():
            if now.year == year:
                avg = sum / now.isocalendar()[1]
            else:
                avg = sum / 52
            LOG.info("Average hours of meetings per week in year %d: %d", year, avg)

    def filter_events_by_exceptions(self, events):
        removed_events = []
        for ex in self.exceptions:
            for event in events:
                if ex in event.summary:
                    removed_events.append(event)
        LOG.info("Removing events as exceptions: %s", removed_events)

        for evt_remove in removed_events:
            if evt_remove in events:
                events.remove(evt_remove)

        return events

    def parse_events(self):
        cal_file = open(self.file, 'rb')
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

    def get_events_by_week(self, all_weeks, events):
        events_by_week = {}
        for event in events:
            week_obj = all_weeks.get_week_obj_of_event(event)
            if not week_obj:
                # TODO log error?
                continue

            if week_obj not in events_by_week:
                events_by_week[week_obj] = []
            events_by_week[week_obj].append(event)
        ordered_dict = collections.OrderedDict(sorted(events_by_week.items()))
        return ordered_dict


if __name__ == '__main__':
    start_time = time.time()

    conf = Config()
    cal_stats = CalendarStats(conf)
    cal_stats.start()

    end_time = time.time()
    LOG.info("Execution of script took %d seconds", end_time - start_time)

