import sys
import webbrowser
import uvicorn


def main():
    port = 8000
    host = "127.0.0.1"
    url = f"http://{host}:{port}"
    print(f"\n=======================================================")
    print(f"  VioWeb: Verificador Notarial de CRLV-e e CNH")
    print(f"  100% Offline | Serpro VIO Decodificador Local")
    print(f"=======================================================")
    print(f"  Acesse no navegador: {url}")
    print(f"  Pressione Ctrl+C para encerrar o servidor.\n")

    # Tenta abrir o navegador automaticamente
    try:
        webbrowser.open(url)
    except Exception:
        pass

    from vioweb.api.app import app

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
