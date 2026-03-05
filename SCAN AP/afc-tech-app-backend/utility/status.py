from datetime import date, timedelta


def compute_filter_status(filter_obj):
    """
    Compute the service status for a ServiceItem (formerly Filter).
    Accepts any object with last_service_date and frequency_days attributes.
    """
    if not filter_obj.last_service_date or not filter_obj.frequency_days:
        return {
            "status": "Pending",
            "next_due_date": None,
            "days_until_due": None,
            "days_overdue": None,
        }

    next_due = filter_obj.last_service_date + timedelta(days=filter_obj.frequency_days)
    today = date.today()

    if today > next_due:
        return {
            "status": "Overdue",
            "next_due_date": next_due.isoformat(),
            "days_until_due": 0,
            "days_overdue": (today - next_due).days,
        }

    if today >= next_due - timedelta(days=7):
        return {
            "status": "Due Soon",
            "next_due_date": next_due.isoformat(),
            "days_until_due": (next_due - today).days,
            "days_overdue": 0,
        }

    return {
        "status": "Completed",
        "next_due_date": next_due.isoformat(),
        "days_until_due": (next_due - today).days,
        "days_overdue": 0,
    }


# Alias so callers using old name still work
compute_service_item_status = compute_filter_status
