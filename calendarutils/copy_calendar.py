import os
import pickle
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_service():
    creds = None
    if os.path.exists('token.pickle'):
        creds = pickle.load(open('token.pickle', 'rb'))
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('calendar', 'v3', credentials=creds)
    return service

def get_calendar_id_by_name(target_name: str, calendar_dicts: Dict[str, Any]) -> str | None:
    for cal_name, dict in calendar_dicts.items():
        if dict["summary"] == target_name:
            return dict["id"]
    raise ValueError("calendar with name '{}' not found".format(target_name))

def list_calendars():
    service = get_service()
    page_token = None

    d = {}
    while True:
        calendars = service.calendarList().list(pageToken=page_token).execute()
        for cal in calendars.get("items", []):
            d[cal["summary"]] = cal
        page_token = calendars.get("nextPageToken")
        if not page_token:
            break
    return d

def copy_events(source_calendar_id,
                source_calendar_name,
                dest_calendar_id,
                dest_calendar_name,
                events: List[Dict[str, Any]]):
    print("Copying events from one calendar to another. ")
    print("Source calendar name: {}, id: {} ".format(source_calendar_name, source_calendar_id))
    print("Destination calendar name: {}, id: {} ".format(dest_calendar_name, dest_calendar_id))

    service = get_service()
    added = []
    for idx, ev in enumerate(events):
        # remove meta-fields that should not be copied
        ev_copy = {k: v for k, v in ev.items() if k not in (
            'id', 'iCalUID', 'etag', 'htmlLink', 'created', 'updated')}
        try:
            progress = f"[{idx + 1} / {len(events)}]"
            print(f"{progress} Copying event: {ev_copy}")
            service.events().insert(calendarId=dest_calendar_id, body=ev_copy).execute()
            print(f"Copied event: {ev.get('summary')} {ev.get('start')} -> {dest_calendar_name}")
            added.append(ev_copy)
        except Exception as e:
            print(f"Failed to copy event {ev.get('summary')} {ev.get('start')}: {e}")

    print(f"Done. Copied {len(added)} events.")


def list_events(calendar_id: str, time_min: str = None, time_max: str = None):
    """
    List all events in a calendar.
    :param calendar_id: Calendar ID (or 'primary')
    :param time_min: Optional ISO 8601 start datetime (e.g. '2025-01-01T00:00:00Z')
    :param time_max: Optional ISO 8601 end datetime
    """
    service = get_service()
    page_token = None
    events = []

    while True:
        params = {
            "calendarId": calendar_id,
            "singleEvents": True,  # expands recurring events
            "orderBy": "startTime",
            "pageToken": page_token,
            "maxResults": 2500
        }
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max

        result = service.events().list(**params).execute()
        items = result.get("items", [])
        for ev in items:
            start = ev["start"].get("dateTime", ev["start"].get("date"))
            end = ev["end"].get("dateTime", ev["end"].get("date"))
            summary = ev.get("summary", "(no title)")
            print(f"{start} → {end}: {summary}")
            events.append(ev)

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    print(f"\nTotal events found: {len(events)}")
    return events

def get_events_created_today(calendar_id: str):
    """
    Lists all events created today and deletes them.
    """
    service = get_service()

    # Start of today in UTC
    # today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    # tomorrow_start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    page_token = None
    found = []
    while True:
        events_res = service.events().list(
            calendarId=calendar_id,
            # timeMin=today_start,
            # timeMax=tomorrow_start,
            singleEvents=True,
            orderBy="startTime",
            pageToken=page_token
        ).execute()

        items = events_res.get("items", [])
        for ev in items:
            created = ev.get("created")
            summary = ev.get("summary", "(no title)")
            if created:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                if created_dt.date() == datetime.now(timezone.utc).date():
                    found.append(ev)
                    print(f"Found event created today: {summary} (created date: {created_dt.isoformat()})")

        page_token = events_res.get("nextPageToken")
        if not page_token:
            break

    print(f"Done. Found {len(found)} events created today.")
    return found

def remove_events(calendar_id, events: List[dict]):
    """
    Removes supplied events from the calendar.
    """
    service = get_service()
    deleted = []

    for ev in events:
        created = ev.get("created")
        summary = ev.get("summary", "(no title)")
        try:
            print(f"Deleting event. Summary:{summary}, created:{created}")
            service.events().delete(calendarId=calendar_id, eventId=ev["id"]).execute()
            print(f"Deleted event. Summary:{summary}, created:{created}")
            deleted.append(ev)
        except Exception as e:
            print(f"Failed to delete event {summary}: {e}")

    print(f"Done. Deleted {len(deleted)} events.")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Copy events from one Google Calendar to another.')
    parser.add_argument('--source', required=True, help='Source calendar name')
    parser.add_argument('--dest', required=True, help='Destination calendar name')
    parser.add_argument('--after', required=False, help='Start time (ISO 8601), e.g. 2020-01-01T00:00:00Z')
    parser.add_argument('--before', required=False, help='End time (ISO 8601)')
    args = parser.parse_args()
    calendar_dicts = list_calendars()
    calendar_names = list(calendar_dicts.keys())
    src_cal_id = get_calendar_id_by_name(args.source, calendar_dicts)
    dest_cal_id = get_calendar_id_by_name(args.dest, calendar_dicts)



    src_events = list_events(src_cal_id, time_min=args.before, time_max=args.after)
    copy_events(src_cal_id, args.source, dest_cal_id, args.dest, src_events)

    # Additional functionality
    # list_events(src_cal_id, args.after, args.before)
    # events = get_events_created_today(dest_cal_id)
    # remove_events(dest_cal_id, events)
