from app import create_app

app = create_app()

# CLI commands from app/__init__.py will be registered on this 'app' instance.

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)