#!/usr/bin/env python3
"""Cliente de conversa no terminal para o assistente local."""
import argparse
import http.client
import json
import os
import shlex
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from assistente import carrega_config, responde


ORCAMENTO_PADRAO = 12000


def le_documentos(pasta):
    documentos = []
    if not pasta or not os.path.isdir(pasta):
        return documentos
    for nome in sorted(os.listdir(pasta)):
        caminho = os.path.join(pasta, nome)
        if os.path.isfile(caminho) and nome.lower().endswith((".txt", ".md")):
            try:
                with open(caminho, encoding="utf-8") as f:
                    documentos.append({"titulo": nome, "texto": f.read()})
            except (OSError, UnicodeError) as e:
                print(f"Aviso: não consegui ler {nome}: {e}", file=sys.stderr)
    return documentos


def corta_historico(historico, orçamento):
    """Remove mensagens antigas, preservando a mensagem mais recente."""
    total = sum(len(str(m.get("content", ""))) for m in historico)
    while len(historico) > 1 and total > orçamento:
        total -= len(str(historico[0].get("content", "")))
        historico.pop(0)


def url_health(url, timeout=1.0):
    u = urllib.parse.urlsplit(url.rstrip("/") + "/health")
    if u.scheme not in ("http", "https") or not u.hostname:
        return False
    cls = http.client.HTTPSConnection if u.scheme == "https" else http.client.HTTPConnection
    conn = cls(u.hostname, u.port, timeout=timeout)
    try:
        conn.request("GET", (u.path or "/") + ("?" + u.query if u.query else ""))
        resp = conn.getresponse()
        resp.read(256)
        return 200 <= resp.status < 300
    except (OSError, http.client.HTTPException):
        return False
    finally:
        conn.close()


class ServidorProprio:
    """Gerencia apenas o subprocesso iniciado por esta instância."""
    def __init__(self, url, comando, comando_cpu=None):
        self.url = url
        self.comandos = [comando] + ([comando_cpu] if comando_cpu else [])
        self.indice = 0
        self.processo = None
        self.falhas = 0

    def _inicia(self):
        comando = self.comandos[self.indice]
        if not comando:
            return
        try:
            # Sem shell: o comando é uma lista de argumentos, nunca conteúdo do modelo.
            self.processo = subprocess.Popen(shlex.split(comando))
        except (OSError, ValueError) as e:
            self.processo = None
            raise RuntimeError(f"Não consegui iniciar o servidor: {e}") from e

    def aguarda_saude(self, limite=60):
        fim = time.monotonic() + limite
        while time.monotonic() < fim:
            if self.processo is not None and self.processo.poll() is not None:
                return False
            if url_health(self.url):
                return True
            time.sleep(.25)
        return False

    def inicia_e_aguarda(self):
        self._inicia()
        if not self.aguarda_saude():
            self.encerra()
            raise RuntimeError("O servidor iniciado não respondeu a /health dentro do prazo.")

    def encerra(self):
        p, self.processo = self.processo, None
        if p is None or p.poll() is not None:
            return
        p.terminate()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()

    def falha(self):
        """Registra falha; na segunda seguida troca para CPU, se configurado."""
        self.falhas += 1
        self.encerra()
        if self.falhas >= 2 and len(self.comandos) > 1 and self.indice == 0:
            self.indice = 1
            print("O servidor falhou duas vezes. Vou tentar a versão de reserva em CPU.")
        else:
            print("O servidor parou de responder. Vou tentar reiniciá-lo.")
        self.inicia_e_aguarda()

    def sucesso(self):
        self.falhas = 0


def conversa_terminal(args):
    cfg = carrega_config(args.config)
    documentos = le_documentos(args.docs)
    historico = []
    servidor = ServidorProprio(args.url, args.servidor, args.servidor_cpu) if args.servidor else None
    if servidor:
        try:
            servidor.inicia_e_aguarda()
        except Exception:
            servidor.encerra()
            raise
        print("Servidor local pronto.")
    print("Conversa pronta. Use /sair, /novo, /docs ou /estado.")
    ultimo_estado = None
    try:
        while True:
            try:
                entrada = input("Você: ")
            except EOFError:
                break
            comando = entrada.strip()
            if comando == "/sair":
                break
            if comando == "/novo":
                historico.clear()
                print("Histórico zerado.")
                continue
            if comando == "/docs":
                documentos = le_documentos(args.docs)
                if documentos:
                    print("Documentos disponíveis:")
                    for d in documentos:
                        print(f"- {d['titulo']}")
                else:
                    print("Nenhum documento .txt ou .md disponível.")
                continue
            if comando == "/estado":
                if not ultimo_estado:
                    print("Ainda não há resposta nesta conversa.")
                else:
                    print("Última resposta: "
                          f"{ultimo_estado['duracao']:.2f} s; "
                          f"1º token em {ultimo_estado['primeiro']}; "
                          f"{ultimo_estado['velocidade']} tokens/s.")
                continue
            if not entrada.strip():
                continue

            if servidor and not url_health(args.url):
                try:
                    servidor.falha()
                except Exception as e:
                    print(f"Não consegui recuperar o servidor: {e}")
                    continue
            historico.append({"role": "user", "content": entrada})
            corta_historico(historico, args.orcamento_caracteres)
            print("Assistente: ", end="", flush=True)
            interrompida = False
            try:
                r = responde(cfg, args.url, historico, documentos=documentos,
                             max_tokens=args.max_tokens, chave=args.chave,
                             ao_receber=lambda trecho: (print(trecho, end="", flush=True)))
                print()
                texto = r.get("texto") or ""
                historico.append({"role": "assistant", "content": texto})
                corta_historico(historico, args.orcamento_caracteres)
                duracao = float(r.get("t_total") or 0)
                n = r.get("tokens_resposta")
                velocidade = (f"{n / duracao:.1f}" if n is not None and duracao > 0 else "indisponível")
                primeiro = (f"{r['t_primeiro']:.2f} s" if r.get("t_primeiro") is not None else "indisponível")
                ultimo_estado = {"duracao": duracao, "primeiro": primeiro, "velocidade": velocidade}
                if servidor:
                    servidor.sucesso()
            except KeyboardInterrupt:
                interrompida = True
                print("\nResposta interrompida. A conversa continua.")
                # Mensagem do usuário sem resposta não deve contaminar o histórico.
                if historico and historico[-1].get("role") == "user":
                    historico.pop()
            except Exception as e:
                print(f"\nErro ao obter resposta: {e}")
                if historico and historico[-1].get("role") == "user":
                    historico.pop()
                falha_travamento = "travamento" in str(e).lower()
                servidor_sem_saude = bool(servidor and not url_health(args.url))
                if servidor and (falha_travamento or servidor_sem_saude):
                    try:
                        servidor.falha()
                    except Exception as rec:
                        print(f"Não consegui recuperar o servidor: {rec}")
            if interrompida:
                continue
    except KeyboardInterrupt:
        print("\nConversa encerrada.")
    finally:
        if servidor:
            servidor.encerra()


# ---------------------------------------------------------------- autoteste com servidor HTTP falso
class _ServidorFalso(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def autoteste():
    estado = {"modo": "normal"}

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        def log_message(self, *_):
            pass
        def do_GET(self):
            status = 200 if self.path == "/health" and estado["modo"] != "queda" else 503
            self.send_response(status)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if estado["modo"] == "queda":
                self.connection.shutdown(1)
                self.connection.close()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.flush()
            if estado["modo"] == "travamento":
                time.sleep(.6)
                return
            eventos = [
                {"choices": [{"delta": {"content": "Olá"}, "finish_reason": None}]},
                {"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 3, "completion_tokens": 1}},
            ]
            for e in eventos:
                self.wfile.write(("data: " + json.dumps(e) + "\n\n").encode())
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

    srv = _ServidorFalso(("127.0.0.1", 0), Handler)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        from cliente import conversa as conversa_cliente
        partes = []
        r = conversa_cliente(url, [{"role": "user", "content": "oi"}], timeout=1, ao_receber=partes.append)
        assert "".join(partes) == "Olá" and r["texto"] == "Olá" and r["tokens_resposta"] == 1
        estado["modo"] = "travamento"
        try:
            conversa_cliente(url, [{"role": "user", "content": "oi"}], timeout=.2)
            raise AssertionError("travamento não detectado")
        except TimeoutError as e:
            assert "travamento" in str(e)
        estado["modo"] = "queda"
        assert not url_health(url, .2)
        try:
            conversa_cliente(url, [{"role": "user", "content": "oi"}], timeout=.3)
            raise AssertionError("queda não detectada")
        except (ConnectionError, TimeoutError):
            pass
        # Confere a regra da segunda falha sem iniciar ou encerrar processos reais.
        ger = ServidorProprio(url, "servidor-principal", "servidor-cpu")
        ger.encerra = lambda: None
        ger.inicia_e_aguarda = lambda: None
        ger.falha()
        assert ger.indice == 0 and ger.falhas == 1
        ger.falha()
        assert ger.indice == 1 and ger.falhas == 2
    finally:
        srv.shutdown()
        srv.server_close()
        th.join(timeout=2)
    print("Autoteste aprovado: streaming SSE, travamento, queda e troca para reserva na segunda falha.")


def main():
    p = argparse.ArgumentParser(description="Converse com o assistente local no terminal.")
    p.add_argument("--config")
    p.add_argument("--url", default="http://127.0.0.1:8081")
    p.add_argument("--chave")
    p.add_argument("--docs")
    p.add_argument("--servidor")
    p.add_argument("--servidor-cpu")
    p.add_argument("--orcamento-caracteres", type=int, default=ORCAMENTO_PADRAO)
    p.add_argument("--max-tokens", type=int, default=400)
    p.add_argument("--autoteste", action="store_true")
    args = p.parse_args()
    if args.autoteste:
        autoteste()
        return 0
    if not args.config:
        p.error("--config é obrigatório, exceto com --autoteste")
    if args.orcamento_caracteres < 1:
        p.error("--orcamento-caracteres deve ser positivo")
    if args.servidor_cpu and not args.servidor:
        p.error("--servidor-cpu requer --servidor")
    conversa_terminal(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
