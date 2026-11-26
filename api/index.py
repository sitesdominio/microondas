import os, time, math, html
from datetime import datetime, timezone
from flask import Flask, request, redirect, make_response
import psycopg
from psycopg.rows import dict_row

app = Flask(__name__)

def connect():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL não configurada na Vercel.")
    return psycopg.connect(url, row_factory=dict_row, connect_timeout=8)

def advance(cur, now):
    # Serializa atualizações da fila para evitar dois requests avançarem o mesmo usuário.
    cur.execute("SELECT pg_advisory_xact_lock(684210)")
    next_start = now
    while True:
        row = cur.execute("""SELECT id, tempo_minutos AS minutos,
          extract(epoch from inicio_uso_em)::double precision AS inicio
          FROM public.fila WHERE finalizado_em IS NULL
          ORDER BY entrada_em,id LIMIT 1 FOR UPDATE""").fetchone()
        if not row: return
        start = row["inicio"]
        if start is None:
            start = next_start
            cur.execute("UPDATE public.fila SET inicio_uso_em=to_timestamp(%s) WHERE id=%s",(start,row["id"]))
        end = start + row["minutos"]*60
        if now < end: return
        cur.execute("UPDATE public.fila SET finalizado_em=to_timestamp(%s) WHERE id=%s",(end,row["id"]))
        next_start = end

def render(title, body, refresh=False, status=200):
    refresh_tag = '<meta http-equiv="refresh" content="2">' if refresh else ""
    page = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>{refresh_tag}<link rel="stylesheet" href="/style.css"></head><body><main class="wrap">{body}</main></body></html>"""
    response=make_response(page,status)
    response.headers["Cache-Control"]="no-store"
    return response

def entry(message="", success=False, status=200):
    note = f'<p class="{"success" if success else "error"}" role="status">{html.escape(message)}</p>' if message else ""
    return render("Entrada na fila",f'<section class="panel"><p class="eyebrow">GERENCIAMENTO DE FILAS</p><h1>Entre na fila</h1><p>Informe sua matrícula para começar.</p>{note}<form action="/validar" method="post"><label for="matricula">Matrícula</label><input id="matricula" name="matricula" required autofocus autocomplete="off" inputmode="numeric" maxlength="20"><button type="submit">Continuar</button></form></section>',status=status)

def choose_time(matricula,nome):
    options="".join(f'<option value="{i}">{i} min</option>' for i in range(1,9))
    return render("Tempo de utilização",f'<section class="panel"><p class="eyebrow">MATRÍCULA VALIDADA</p><h1>Olá, {html.escape(nome)}</h1><form action="/entrar" method="post"><input type="hidden" name="matricula" value="{html.escape(matricula,quote=True)}"><label for="minutos">Tempo de utilização</label><select id="minutos" name="minutos">{options}</select><button type="submit">Entrar na fila</button></form><a href="/">Voltar</a></section>')

def validate_user(matricula):
    with connect() as con:
        with con.transaction():
            cur=con.cursor()
            advance(cur,time.time())
            user=cur.execute("SELECT nome FROM public.usuarios WHERE matricula=%s",(matricula,)).fetchone()
            active=cur.execute("SELECT 1 FROM public.fila WHERE matricula=%s AND finalizado_em IS NULL",(matricula,)).fetchone()
            if not user: raise ValueError("Matrícula não cadastrada. Procure o responsável pelo cadastro.")
            if active: raise ValueError("Esta matrícula já está na fila.")
            return user["nome"]

def add_queue(matricula,minutes):
    if minutes not in range(1,9): raise ValueError("Selecione um tempo inteiro de 1 a 8 minutos.")
    with connect() as con:
        with con.transaction():
            cur=con.cursor()
            advance(cur,time.time())
            if not cur.execute("SELECT 1 FROM public.usuarios WHERE matricula=%s",(matricula,)).fetchone():
                raise ValueError("Matrícula não cadastrada. Procure o responsável pelo cadastro.")
            if cur.execute("SELECT 1 FROM public.fila WHERE matricula=%s AND finalizado_em IS NULL",(matricula,)).fetchone():
                raise ValueError("Esta matrícula já está na fila.")
            cur.execute("INSERT INTO public.fila(matricula,tempo_minutos) VALUES (%s,%s)",(matricula,minutes))

def queue_snapshot():
    with connect() as con:
        with con.transaction():
            cur=con.cursor()
            now=time.time()
            advance(cur,now)
            rows=cur.execute("""SELECT q.id,q.matricula,q.tempo_minutos AS minutos,
              extract(epoch from q.inicio_uso_em)::double precision AS inicio,u.nome
              FROM public.fila q JOIN public.usuarios u USING(matricula)
              WHERE q.finalizado_em IS NULL ORDER BY q.entrada_em,q.id""").fetchall()
            return [dict(r) for r in rows],now

@app.get("/")
def home():
    return entry()

@app.get("/style.css")
def css():
    # The file is also deployed as a Vercel static asset.
    from pathlib import Path
    p=Path(__file__).resolve().parent.parent/"public"/"style.css"
    if p.exists(): return p.read_text(),200,{"Content-Type":"text/css; charset=utf-8"}
    return "",404

@app.post("/validar")
def validate():
    matricula=request.form.get("matricula","").strip()
    if not matricula: return entry("Informe a matrícula.")
    try: return choose_time(matricula,validate_user(matricula))
    except ValueError as e: return entry(str(e),status=400)
    except Exception: return entry("Não foi possível acessar o banco. Verifique a configuração do sistema.",status=500)

@app.post("/entrar")
def join():
    matricula=request.form.get("matricula","").strip()
    raw=request.form.get("minutos","")
    if raw not in [str(i) for i in range(1,9)]: return entry("Tempo inválido.",status=400)
    try:
        add_queue(matricula,int(raw))
        return entry("Entrada na fila confirmada.",True)
    except ValueError as e: return entry(str(e),status=400)
    except Exception: return entry("Não foi possível registrar na fila. Verifique a configuração do sistema.",status=500)

@app.get("/telao")
def display():
    try:
        rows,now=queue_snapshot()
        if not rows:
            body='<section class="active"><p class="eyebrow">EM UTILIZAÇÃO</p><h1>Fila livre</h1><p>Aguardando usuários</p></section>'
        else:
            r=rows[0]
            seconds=max(0,math.ceil((r["inicio"] or now)+r["minutos"]*60-now))
            body=f'<section class="active"><p class="eyebrow">EM UTILIZAÇÃO · POSIÇÃO 1</p><h1>{html.escape(r["nome"])}</h1><div class="timer">{seconds//60:02}:{seconds%60:02}</div><p>Tempo restante</p></section>'
        body+='<section class="waiting"><h2>Próximos da fila</h2>'
        body+="".join(f'<div class="queue-row"><span class="position">{i}</span><strong>{html.escape(r["nome"])}</strong><span>{r["minutos"]} min</span></div>' for i,r in enumerate(rows[1:],2)) or "<p>Nenhum usuário aguardando.</p>"
        return render("Telão da fila",body+"</section>",refresh=True)
    except Exception:
        return render("Telão da fila",'<section class="panel"><h1>Fila indisponível</h1><p>Não foi possível consultar o banco. Verifique DATABASE_URL.</p><a href="/">Voltar</a></section>',status=500)

@app.get("/health")
def health():
    try:
        with connect() as con: con.execute("SELECT 1")
        return {"status":"ok","database":"connected"}
    except Exception:
        return {"status":"error","database":"unavailable"},500
