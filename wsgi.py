from app import create_app

app = create_app(config_name="development")

if __name__ == "__main__":
    print('starting app...')
    app.run()
