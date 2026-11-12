import webbrowser


def main():
    try:
        import uvicorn
        from vioweb.api.app import app
    except ImportError:
        print("\n[ERRO] Dependências de servidor não instaladas.")
        print("Para rodar o servidor local, instale com:")
        print("    pip install 'vioweb[server]'\n")
        return

    port = 8000
    host = "127.0.0.1"
    url = f"http://{host}:{port}"
    print("\n=======================================================")
    print("  VioWeb: Verificador Notarial de CRLV-e e CNH")
    print("  100% Offline | Serpro VIO Decodificador Local")
    print("=======================================================")
    print(f"  Acesse no navegador: {url}")
    print("  Pressione Ctrl+C para encerrar o servidor.\n")

    # Tenta abrir o navegador automaticamente
    try:
        webbrowser.open(url)
    except Exception:
        pass

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
