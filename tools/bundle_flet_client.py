"""
Prepara o cliente desktop do Flet (flet.exe + DLLs Flutter) para ser embutido no executável.

Sem isso, o pacote `flet_desktop` baixa o cliente do GitHub na primeira execução
em cada máquina. Em redes de clientes com proxy/firewall de inspeção SSL ou sem
certificados raiz atualizados, esse download falha com:
    [SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer certificate

O `flet_desktop` procura primeiro por `flet_desktop/app/flet-windows.zip` dentro do
bundle do PyInstaller; se existir, extrai localmente e não acessa a internet.

Uso:
    python tools/bundle_flet_client.py <arquivo_zip_de_saida>
"""

import os
import sys
import zipfile
from pathlib import Path

import flet_desktop


def main() -> int:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "build/flet_client/flet-windows.zip")

    # Garante que o cliente está no cache local (~/.flet/client/...), baixando se preciso.
    # Na máquina de build a internet funciona normalmente.
    cache_dir = Path(flet_desktop.ensure_client_cached())
    client_dir = cache_dir / "flet"
    if not (client_dir / "flet.exe").is_file():
        print(f"ERRO: flet.exe não encontrado em {client_dir}", file=sys.stderr)
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    # O zip precisa conter a pasta "flet/" na raiz, pois o flet_desktop
    # executa <cache>/flet/flet.exe após a extração.
    count = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(client_dir):
            for name in files:
                full = Path(root) / name
                zf.write(full, full.relative_to(cache_dir).as_posix())
                count += 1

    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"Cliente Flet empacotado: {output} ({count} arquivos, {size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
