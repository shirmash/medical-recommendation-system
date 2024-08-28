from datetime import timedelta, datetime

##helper functions
def get_timedelta(hours, granularity):
    if granularity == 'hours':
        return timedelta(hours=hours)
    elif granularity == 'days':
        return timedelta(days=hours / 24)
    elif granularity == 'minutes':
        return timedelta(minutes=hours * 60)
    elif granularity == 'seconds':
        return timedelta(seconds=hours * 3600)
    else:
        return timedelta(hours=hours)

def parse_datetime(date_str):
    if isinstance( date_str, str ):
        return datetime.strptime( date_str, "%Y-%m-%d %H:%M:%S" )
    return date_str
    # return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

def deal_with_good_before_and_good_after(hemoglobin_sample, kb_hemoglobin):
    granularity = kb_hemoglobin['granularity']
    hemoglobin_sample['Valid start time before'] = (parse_datetime(hemoglobin_sample['Valid start time']) - get_timedelta(kb_hemoglobin['good before'], granularity))
    hemoglobin_sample['Valid end time after'] = parse_datetime(hemoglobin_sample['Valid end time']) + get_timedelta(kb_hemoglobin['good after'], granularity)

    return hemoglobin_sample

def format_datetime(datetime):
    return datetime.strftime('%Y-%m-%d %H:%M:%S')
def parse_time(time_str):
        return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')