from app import create_app

app = create_app()

if __name__ == '__main__':
    # host='0.0.0.0' permite acceso desde otros ordenadores de la red
    # port=5001 cambialo si ese puerto ya esta ocupado por otra app
    app.run(host='0.0.0.0', port=5001, debug=True)