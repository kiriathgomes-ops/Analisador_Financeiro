import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# ============================================================
# CONFIGURAÇÃO
# ============================================================
STREAMLIT_URL = "http://localhost:8501"
CLOUDFLARED_EXE = Path.home() / "Downloads" / "cloudflared.exe"

# ============================================================
# FUNÇÕES
# ============================================================
def verificar_streamlit():
    """Confirma que o Streamlit está respondendo localmente."""
    try:
        req = urllib.request.Request(
            STREAMLIT_URL,
            headers={"User-Agent": "Cloudflare-Tunnel-Launcher"}
        )
        with urllib.request.urlopen(req, timeout=5) as resposta:
            return resposta.status == 200
    except Exception:
        return False


def localizar_cloudflared():
    """Localiza cloudflared.exe no caminho configurado ou no PATH."""
    if CLOUDFLARED_EXE.is_file():
        return str(CLOUDFLARED_EXE)

    encontrado = shutil.which("cloudflared")
    if encontrado:
        return encontrado

    return None


def iniciar_tunel(executavel):
    """Inicia o Quick Tunnel e exibe o link assim que ele aparecer."""
    comando = [
        executavel,
        "tunnel",
        "--url",
        STREAMLIT_URL,
    ]

    print("\nIniciando Cloudflare Tunnel...")
    print("Destino local:", STREAMLIT_URL)
    print("Mantenha esta janela aberta enquanto estiver compartilhando.\n")

    processo = subprocess.Popen(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    link_encontrado = False

    try:
        for linha in processo.stdout:
            print(linha, end="")

            correspondencia = re.search(
                r"https://[a-z0-9-]+\.trycloudflare\.com",
                linha,
                re.IGNORECASE,
            )
            if correspondencia and not link_encontrado:
                link = correspondencia.group(0)
                link_encontrado = True
                print("\n" + "=" * 64)
                print("LINK PÚBLICO DO STREAMLIT:")
                print(link)
                print("=" * 64 + "\n")

        codigo = processo.wait()
        if codigo != 0:
            print(f"\nO cloudflared encerrou com código {codigo}.")
    except KeyboardInterrupt:
        print("\nEncerrando o túnel...")
        processo.terminate()
        try:
            processo.wait(timeout=5)
        except subprocess.TimeoutExpired:
            processo.kill()
        print("Túnel encerrado. O link temporário deixou de funcionar.")
    finally:
        if processo.poll() is None:
            processo.terminate()


def main():
    print("=" * 64)
    print("   INICIADOR CLOUDFLARE TUNNEL — STREAMLIT")
    print("=" * 64)

    executavel = localizar_cloudflared()
    if not executavel:
        print("\nERRO: cloudflared.exe não foi encontrado.")
        print("Coloque-o em:", CLOUDFLARED_EXE)
        print("Ou adicione o cloudflared ao PATH do Windows.")
        input("\nPressione Enter para sair...")
        sys.exit(1)

    print("\nCloudflared encontrado:", executavel)

    if not verificar_streamlit():
        print("\nERRO: não consegui acessar", STREAMLIT_URL)
        print("Inicie seu Streamlit em outro terminal, por exemplo:")
        print(r"  cd E:\ProjetosPython\Analisador_Financeiro")
        print("  python -m streamlit run app.py")
        print("\nSe o arquivo principal não for app.py, substitua pelo nome correto.")
        input("\nPressione Enter para sair...")
        sys.exit(1)

    print("Streamlit local: OK (HTTP 200)")
    iniciar_tunel(executavel)


if __name__ == "__main__":
    main()
