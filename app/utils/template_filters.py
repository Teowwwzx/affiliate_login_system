# app/utils/template_filters.py

def format_currency(amount):
    """Format a number as currency with 2 decimal places and thousand separators."""
    try:
        return "${:,.2f}".format(float(amount))
    except (ValueError, TypeError):
        return str(amount)  # Return as-is if not a valid number

# This is the function that will be called by Flask to register filters
def register_filters(app):
    """Registers custom Jinja2 filters with the Flask app."""
    app.jinja_env.filters['format_currency'] = format_currency
    # Add other filters here if needed
