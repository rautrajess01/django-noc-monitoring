# In your utils.py
import datetime
import re  # <--- NEW: Import regular expression library
from nepali_datetime import date as NepaliDate
from nepali_datetime import datetime as NepaliDateTime

BS_MONTH_MAP = {
    "baisakh": 1, "jestha": 2, "ashadh": 3, "shrawan": 4, "bhadra": 5,
    "ashwin": 6, "kartik": 7, "mangsir": 8, "poush": 9, "magh": 10,
    "falgun": 11, "chaitra": 12, "bai": 1, "jes": 2, "asa": 3, "shr": 4, 
    "bha": 5, "ash": 6, "kar": 7, "man": 8, "pou": 9, "mag": 10, 
    "fal": 11, "cha": 12,
}

# <--- NEW: Add a map for AD months for more flexibility --->
AD_MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def get_time_range(request):
    start_date_ad_str = request.GET.get("start_date")
    end_date_ad_str = request.GET.get("end_date")
    bs_date_query = request.GET.get("date_query")

    start_time, end_time = None, None

    if start_date_ad_str and end_date_ad_str:
        # This part remains the same
        try:
            start_ad_date = datetime.datetime.strptime(start_date_ad_str, "%Y-%m-%d").date()
            end_ad_date = datetime.datetime.strptime(end_date_ad_str, "%Y-%m-%d").date()
            start_time = datetime.datetime.combine(start_ad_date, datetime.time.min)
            end_time = datetime.datetime.combine(end_ad_date, datetime.time.max)
            return start_time, end_time
        except ValueError:
            return None, None

    elif bs_date_query:
        try:
            # <--- REPLACED: The entire parsing logic is now much more robust --->
            parts = bs_date_query.strip().lower().split()
            start_ad_date, end_ad_date = None, None
            
            # --- Handle full month query (e.g., "Baisakh" or "July") ---
            if len(parts) == 1:
                month_name = parts[0]
                if month_name in BS_MONTH_MAP:
                    bs_month_num = BS_MONTH_MAP[month_name]
                    current_bs_year = NepaliDate.today().year
                    days_in_month = NepaliDate.get_days_in_month(current_bs_year, bs_month_num)
                    start_bs = NepaliDate(current_bs_year, bs_month_num, 1)
                    end_bs = NepaliDate(current_bs_year, bs_month_num, days_in_month)
                    start_ad_date, end_ad_date = start_bs.to_gregorian(), end_bs.to_gregorian()
                elif month_name in AD_MONTH_MAP:
                    ad_month_num = AD_MONTH_MAP[month_name]
                    current_ad_year = datetime.date.today().year
                    # To get last day of month, go to first of next month and subtract one day
                    next_month = ad_month_num % 12 + 1
                    next_year = current_ad_year if ad_month_num != 12 else current_ad_year + 1
                    last_day = datetime.date(next_year, next_month, 1) - datetime.timedelta(days=1)
                    start_ad_date = datetime.date(current_ad_year, ad_month_num, 1)
                    end_ad_date = last_day

            # --- Handle daily query (e.g., "Baisakh 15", "July 1", "15 Baisakh", "1. July") ---
            elif len(parts) == 2:
                # Determine which part is the month and which is the day
                part1, part2 = parts[0], parts[1]
                day_str, month_name = (None, None)

                if part1.isdigit() or re.match(r'^\d+', part1): # Checks if it starts with a digit
                    day_str, month_name = part1, part2
                elif part2.isdigit() or re.match(r'^\d+', part2):
                    month_name, day_str = part1, part2
                
                if day_str and month_name:
                    # Clean the day string, removing any non-digit characters (like '.')
                    day_num = int(re.sub(r'\D', '', day_str))

                    if month_name in BS_MONTH_MAP:
                        bs_month_num = BS_MONTH_MAP[month_name]
                        current_bs_year = NepaliDate.today().year
                        target_bs = NepaliDate(current_bs_year, bs_month_num, day_num)
                        start_ad_date = end_ad_date = target_bs.to_gregorian()
                    elif month_name in AD_MONTH_MAP:
                        ad_month_num = AD_MONTH_MAP[month_name]
                        current_ad_year = datetime.date.today().year
                        target_ad = datetime.date(current_ad_year, ad_month_num, day_num)
                        start_ad_date = end_ad_date = target_ad

            # --- Final combination for BS/AD queries ---
            if start_ad_date and end_ad_date:
                start_time = datetime.datetime.combine(start_ad_date, datetime.time.min)
                end_time = datetime.datetime.combine(end_ad_date, datetime.time.max)
                return start_time, end_time

        except (ValueError, IndexError, TypeError):
            # Catch errors from bad dates (Baisakh 33), bad formats, etc.
            return None, None
    
    else:
        # Default behavior remains the same
        current_bs_year = NepaliDate.today().year
        start_bs = NepaliDate(current_bs_year, 1, 1)
        start_ad_date = start_bs.to_gregorian()
        start_time = datetime.datetime.combine(start_ad_date, datetime.time.min)
        end_time = datetime.datetime.now()
        return start_time, end_time

    return None, None
from collections import Counter

def find_likely_root_cause(reasons_list, total_down_events=0):
    if not reasons_list:
        return "N/A"
    
    # Clean and count reasons
    clean_reasons = [reason.strip() for reason in reasons_list if reason.strip()]
    if not clean_reasons:
        return "Symptom-only (e.g. Reboot)"
    
    reason_counts = Counter(clean_reasons)
    
    # Define reason categories and their root cause priorities
    # Higher priority = more likely to be actual root cause (not symptom)
    reason_categories = {
        # Power Issues (High Priority - Root Causes)
        'Power': {'priority': 9, 'reasons': [
            'Power', 'Power Issue', 'MCB Trip', 'Voltage Issue', 'UPS Hung/Rebooted',
            'Battery Issue', 'Short circuit', 'Stabilizer Issue', 'UPS Damage', 
            'UPS Issue', 'Backup issue', 'Power Chord Loose', 'UPS Replacement',
            'AVR Issue', 'MCB Damage', 'Power Chord Issue', 'Rectifier Issue',
            'Circuit Breaker OFF', 'Generator not Operated on time', 'Sub-meter Issue'
        ]},
        
        # Fiber Issues (High Priority - Root Causes)
        'Fiber': {'priority': 9, 'reasons': [
            'Fiber Breakage', 'Fiber Burnt', 'Fiber Issue', 'Fiber Losses', 'Patch cord issue',
            'Cable Issue', 'Fiber Replacement', 'RF Cable Issue', 'Repalced Ethernet cable',
            'Link down', 'Link Flap', 'CRC Issue', 'Core Damage', 'Ethernet Cable loose',
            'Plug/Unplug Ethernet Cable', 'Path Issue', 'Losses', 'Ethernet Cable Damage',
            'Fiber Maintenance', 'ADDS fiber maintanence'
        ]},
        
        # CT Line Issues (Very High Priority - Infrastructure Root Cause)
        'CT Line Issue': {'priority': 10, 'reasons': [
            'CT Line Issue/Backup Drained', 'CT Line Issue', 'CT line outage', 'CT Line Fluctuation'
        ]},
        
        # Device Issues (High Priority - Hardware Root Causes)
        'Device': {'priority': 8, 'reasons': [
            'Switch Issue', 'POE device Damage', 'Device Issue', 'Port issue', 
            'Device Replacement', 'Card Issue', 'chassis issue', 'SFP Issue',
            'Wireless Device Damage', 'Device Hang', 'Switch Decommissioned',
            'MUX Issue', 'OLP issue', 'MPLS Issue', 'ATS Issue'
        ]},
        
        # Temperature Issues (High Priority - Environmental Root Cause)
        'Temperature Issue': {'priority': 8, 'reasons': [
            'HIgh Temperature', 'Temperature Issue'
        ]},
        
        # Traffic Issues (Medium Priority)
        'Traffic Issue': {'priority': 6, 'reasons': [
            'Congestion', 'Traffic Issue', 'Traffic Drop', 'TV issue', 'DTI Traffic Drop',
            'Upstream issue'
        ]},
        
        # Weather Issues (High Priority - External Root Cause)
        'Weather': {'priority': 8, 'reasons': [
            'Manual Down/Weather', 'Weather Unfavourable'
        ]},
        
        # Maintenance (Medium Priority - Planned)
        'Maintenance': {'priority': 5, 'reasons': [
            'Working at POP', 'Maintainance', 'Intentional', 'Device Replacement',
            'Manual Down', 'Maintainance', 'POP Shift', 'Link Upgrade', 'Team Working'
        ]},
        
        # Logical Issues (Medium Priority)
        'Logical Issue': {'priority': 6, 'reasons': [
            'Shut/unshut Port', 'Admin Issue', 'Configuration Change', 'Logical Issue',
            'management issue'
        ]},
        
        # Wireless Issues (Medium Priority)
        'Wireless': {'priority': 6, 'reasons': [
            'Configuration Change', 'Radio Rebooted/Soft', 'Wireless Issue'
        ]},
        
        # Symptoms (Low Priority - These are effects, not causes)
        'Reboot': {'priority': 1, 'reasons': [
            'Rebooted', 'Manual Reboot', 'Automatic Rebooted'
        ]},
        
        # External/Uncontrollable (Low Priority for filtering)
        'External': {'priority': 3, 'reasons': [
            'Pole shifting', 'Road Expansion', 'NEA Working'
        ]},
        
        # Terminated/No Issue (Should be excluded)
        'Terminated': {'priority': 0, 'reasons': [
            'Host Removed', 'No need to follow up', 'No Clients', 'Link Decommissioned',
            'Cannot Optimize'
        ]},
        
        # Provider Issues (Medium Priority)
        'Provider Issue': {'priority': 7, 'reasons': [
            'Techmind issue', 'Broadlink issue'
        ]},
        
        # Power Backup Issues (High Priority)
        'Power Backup': {'priority': 8, 'reasons': [
            'No Backup', 'Full Solar POP', 'Backup issue'
        ]},
        
        # Unknown (Lowest Priority)
        'Unknown': {'priority': 0, 'reasons': [
            'Unknown', 'Unknown'
        ]}
    }
    
    # Map each reason to its category and priority
    reason_to_category = {}
    for category, info in reason_categories.items():
        for reason in info['reasons']:
            reason_to_category[reason.lower()] = {
                'category': category,
                'priority': info['priority']
            }
    
    # Categorize the input reasons
    categorized_reasons = {}
    for reason, count in reason_counts.items():
        reason_lower = reason.lower()
        
        # Find matching category (exact match or partial match)
        matched_category = None
        matched_priority = 0
        
        # First try exact match
        if reason_lower in reason_to_category:
            matched_category = reason_to_category[reason_lower]['category']
            matched_priority = reason_to_category[reason_lower]['priority']
        else:
            # Try partial matching
            for mapped_reason, info in reason_to_category.items():
                if mapped_reason in reason_lower or reason_lower in mapped_reason:
                    if info['priority'] > matched_priority:
                        matched_category = info['category']
                        matched_priority = info['priority']
        
        # If no match found, treat as unknown
        if not matched_category:
            matched_category = 'Unknown'
            matched_priority = 0
        
        if matched_category not in categorized_reasons:
            categorized_reasons[matched_category] = {
                'count': 0,
                'priority': matched_priority,
                'examples': []
            }
        
        categorized_reasons[matched_category]['count'] += count
        categorized_reasons[matched_category]['examples'].append(reason)
    
    # Filter out unknown reasons unless they're the only option
    unknown_categories = {k: v for k, v in categorized_reasons.items() if k == 'Unknown'}
    non_unknown_categories = {k: v for k, v in categorized_reasons.items() if k != 'Unknown'}
    
    # Decide which categories to use
    if non_unknown_categories:
        working_categories = non_unknown_categories
    elif len(unknown_categories) == 1 and len(unknown_categories['Unknown']['examples']) == 1:
        working_categories = unknown_categories
    else:
        # Multiple unknowns or mixed, use original
        working_categories = categorized_reasons
    
    # Special handling for devices with 100+ down events
    if total_down_events >= 100:
        # Filter out terminated/no-issue categories
        high_freq_categories = {
            k: v for k, v in working_categories.items() 
            if v['priority'] > 0  # Exclude terminated and unknown
        }
        
        if high_freq_categories:
            # Sort by priority (desc) then by count (desc)
            sorted_categories = sorted(
                high_freq_categories.items(),
                key=lambda x: (-x[1]['priority'], -x[1]['count'])
            )
            
            # For high frequency, prioritize root causes over symptoms
            max_priority = max(cat['priority'] for cat in high_freq_categories.values())
            
            # If we have root causes (priority > 3), filter out symptoms
            if max_priority > 3:
                root_causes = [
                    (cat, info) for cat, info in sorted_categories 
                    if info['priority'] > 3
                ]
                if root_causes:
                    sorted_categories = root_causes
            
            # Return top 2 categories
            top_categories = sorted_categories[:2]
            result_reasons = []
            
            for category, info in top_categories:
                # Use the most common specific reason from this category
                most_common_reason = max(info['examples'], key=lambda x: reason_counts[x])
                result_reasons.append(most_common_reason)
            
            return ", ".join(result_reasons)
    
    # Original logic for devices with < 100 down events
    MIN_OCCURRENCES = 2
    significant_reasons = [
        (r, c) for r, c in reason_counts.most_common() if c >= MIN_OCCURRENCES
    ]
    
    if significant_reasons:
        # Filter out unknown if other significant reasons exist
        non_unknown_significant = [
            (r, c) for r, c in significant_reasons 
            if not any(unknown in r.lower() for unknown in ['unknown'])
        ]
        
        if non_unknown_significant:
            top_reasons = non_unknown_significant[:2]
        else:
            top_reasons = significant_reasons[:2]
    else:
        # No significant reasons, use most common
        all_reasons = list(reason_counts.most_common())
        non_unknown_all = [
            (r, c) for r, c in all_reasons 
            if not any(unknown in r.lower() for unknown in ['unknown'])
        ]
        
        if non_unknown_all:
            top_reasons = non_unknown_all[:2]
        elif len(all_reasons) == 1:  # Only one unknown type
            top_reasons = all_reasons[:1]
        else:
            top_reasons = all_reasons[:2]
    
    return ", ".join(reason for reason, _ in top_reasons)

