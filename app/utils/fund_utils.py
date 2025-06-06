# app/utils/fund_utils.py
from app.database import db
from app.database.models import Fund, FundHistory
from sqlalchemy import func, extract
from datetime import datetime, timedelta
import calendar
from flask import current_app

def generate_monthly_fund_summary(year, month):
    """
    Generates monthly fund summaries for the given year and month and stores them in FundHistory.
    It creates:
    1. A summary record for each distinct 'fund_type' found in Fund entries for that month,
       aggregating sales, payouts, and calculating profits.
    2. An overall monthly summary record ('ALL_TYPES_MONTHLY_SUMMARY') aggregating all fund types.
    The snapshot_date is set to the last day of the specified month.
    Returns True if successful, False otherwise.
    """
    try:
        last_day_of_month_num = calendar.monthrange(year, month)[1]
        last_day_of_month_dt = datetime(year, month, last_day_of_month_num)
        snapshot_date = last_day_of_month_dt.date()

        # Delete existing summaries for this month to prevent duplicates
        existing_summaries = FundHistory.query.filter_by(snapshot_date=snapshot_date).all()
        if existing_summaries:
            for summary in existing_summaries:
                db.session.delete(summary)
            db.session.commit()
            print(f"Deleted {len(existing_summaries)} existing fund history summaries for {year}-{month:02d}.")

        fund_records_for_month = Fund.query.filter(
            extract('year', Fund.created_at) == year,
            extract('month', Fund.created_at) == month
        ).all()

        if not fund_records_for_month:
            print(f"No fund records found for {year}-{month:02d} to create summaries.")
            return True

        summaries_by_type = {}
        all_monthly_sales = 0.0
        all_monthly_payout = 0.0

        for record in fund_records_for_month:
            fund_type = record.fund_type if record.fund_type and record.fund_type.strip() else 'general'
            if fund_type not in summaries_by_type:
                summaries_by_type[fund_type] = {'sales': 0.0, 'payout': 0.0}
            
            current_sales = float(record.sales) if record.sales is not None else 0.0
            current_payout = float(record.payout) if record.payout is not None else 0.0
            
            summaries_by_type[fund_type]['sales'] += current_sales
            summaries_by_type[fund_type]['payout'] += current_payout
            
            all_monthly_sales += current_sales
            all_monthly_payout += current_payout

        summary_records_created = 0

        # Create summaries for each fund_type
        for fund_type, data in summaries_by_type.items():
            type_sales = data['sales']
            type_payout = data['payout']
            type_total_profit = type_sales - type_payout
            type_total_net_profit = (type_sales - type_payout) * 0.30 / 0.5

            new_history_record = FundHistory(
                snapshot_date=snapshot_date,
                fund_type=fund_type,
                sales=type_sales,
                payout=type_payout,
                total_profit=type_total_profit,
                total_net_profit=type_total_net_profit
            )
            db.session.add(new_history_record)
            summary_records_created += 1
            print(f"Prepared summary for type '{fund_type}' for {year}-{month:02d}: Sales={type_sales:.2f}, Payout={type_payout:.2f}")

        # Create overall monthly summary if there were any records
        if fund_records_for_month:
            overall_total_profit = all_monthly_sales - all_monthly_payout
            overall_total_net_profit = (all_monthly_sales - all_monthly_payout) * 0.30 / 0.5

            overall_summary_record = FundHistory(
                snapshot_date=snapshot_date,
                fund_type='MONTHLY_SALES',
                sales=all_monthly_sales,
                payout=all_monthly_payout,
                total_profit=overall_total_profit,
                total_net_profit=overall_total_net_profit
            )
            db.session.add(overall_summary_record)
            summary_records_created += 1
            print(f"Prepared overall monthly summary for {year}-{month:02d}: Total Sales={all_monthly_sales:.2f}, Total Payout={all_monthly_payout:.2f}")

        db.session.commit()
        print(f"Successfully created {summary_records_created} fund history summary records for {year}-{month:02d}.")
        return True

    except Exception as e:
        db.session.rollback()
        log_message = f"Error creating fund history summaries for {year}-{month:02d}: {str(e)}"
        print(log_message)
        # Use current_app.logger if available (within Flask app context)
        if current_app:
            current_app.logger.error(log_message, exc_info=True)
        else:
            # Fallback basic logging if current_app is not available
            import logging
            logging.error(log_message, exc_info=True)
        return False


def generate_summary_for_previous_month():
    """Helper function to generate summary for the immediately preceding month."""
    today = datetime.utcnow()
    first_day_of_current_month = today.replace(day=1)
    last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
    
    prev_month = last_day_of_previous_month.month
    prev_year = last_day_of_previous_month.year
    
    print(f"Attempting to generate summary for previous month: {prev_year}-{prev_month:02d}")
    return generate_monthly_fund_summary(prev_year, prev_month)

