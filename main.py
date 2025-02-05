from app import *

pd.options.display.max_columns = 20


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


@app.before_request
def make_session_permanet():
    session.permanent = True
    app.permanet_session_lifetime = timedelta(minutes=20)


@app.route('/', methods=["GET", "POST"])
def home():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        # Email doesn't exist or password incorrect.
        if not user:
            flash("Email incorreto, tente novamente")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('Senha incorreta, tente novamente')
            return redirect(url_for('login'))
        else:
            login_user(user)
            session['user_name'] = user.name
            session['user_id'] = user.id
            session['admin'] = user.admin
            session['mesa'] = user.mesa
            return redirect(url_for('monitorar'))
    return render_template("login.html", logged_in=current_user.is_authenticated)


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get('email')
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if user:
            flash("Email já cadastrado, faça o login")
            return redirect(url_for('login'))
        hash_and_salted_password = generate_password_hash(
            request.form.get('password'),
            method='pbkdf2:sha256',
            salt_length=8
        )
        time_user = request.form.get("time")
        time = db.session.execute(db.select(Times).where(Times.nome == time_user)).scalar()

        if time is None:
            new_time = Times(
                time=time
            )
            db.session.add(new_time)
            new_user = User(
                email=request.form.get('email'),
                password=hash_and_salted_password,
                name=request.form.get('name'),
                admin=request.form.get('admin'),
                mesa=request.form.get('mesa'),
                id_time=new_time.id,
                time=new_time.time
            )
            db.session.add(new_user)
            db.session.commit()
        else:
            new_user = User(
                email=request.form.get('email'),
                password=hash_and_salted_password,
                name=request.form.get('name'),
                admin=request.form.get('admin'),
                mesa=request.form.get('mesa'),
                id_time=time.id,
                time=time.time
            )
            db.session.add(new_user)
            db.session.commit()
        login_user(new_user)
        session['user_id'] = new_user.id
        session["user_name"] = new_user.name
        session['admin'] = user.admin
        session['mesa'] = user.mesa
        return redirect(url_for("monitorar"))
    return render_template("register.html", logged_in=current_user.is_authenticated)


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        # Email doesn't exist or password incorrect.
        if not user:
            flash("Email incorreto, tente novamente")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('Senha incorreta, tente novamente')
            return redirect(url_for('login'))
        else:
            login_user(user)
            session['user_name'] = user.name
            session['user_id'] = user.id
            session['admin'] = user.admin
            session['mesa'] = user.mesa
            session.permanent = True
            return redirect(url_for('monitorar'))
    return render_template("login.html", logged_in=current_user.is_authenticated)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/monitorar', methods=["POST", "GET"])
@login_required
def monitorar():
    name = session.get('user_name')
    user_id = session.get('user_id')
    admin = session.get("admin")
    mesa = session.get("mesa")

    result = db.session.execute(db.select(Clientes).where(Clientes.id_assessor == user_id))
    clientes = result.scalars()
    return render_template('monitorar.html', user_name=name, user_id=user_id, clientes=clientes, admin=admin, mesa=mesa)


@app.route('/monitorar_tarefas', methods=["POST", "GET"])
@login_required
def monitorar_tarefas():
    name = session.get('user_name')
    user_id = session.get('user_id')
    admin = session.get("admin")
    mesa = session.get("mesa")
    tarefas = db.session.execute(db.select(Tarefas).where(Tarefas.assessor_id == user_id)).scalars()
    return render_template('monitorar_tarefas.html', user_name=name, tarefas=tarefas, admin=admin, mesa=mesa)


@app.route('/cadastrar', methods=["POST", "GET"])
@login_required
def cadastrar():
    if request.method == "POST":
        formato_data = "%Y-%m-%d"
        inicio_str = request.form.get('cliente_desde')
        abertura_str = request.form.get('abertura')
        fechamento_str = request.form.get('fechamento')
        inicio = datetime.strptime(inicio_str, formato_data).date() if inicio_str else None
        abertura = datetime.strptime(abertura_str, formato_data).date() if abertura_str else None
        fechamento = datetime.strptime(fechamento_str, formato_data).date() if fechamento_str else None
        novo = Clientes(
            nome=request.form.get('nome'),
            pj=request.form.get('pj'),
            email=request.form.get('email'),
            telefone=request.form.get('telefone'),
            endereco=request.form.get('endereco'),
            id_assessor=session.get('user_id'),
            assessor=session.get('user_name'),
            conta=request.form.get('conta'),
            cod_bolsa=request.form.get('cod_bolsa'),
            perfil=request.form.get('perfil'),
            valor_estimado=request.form.get('valor_estimado'),
            valor_atual=request.form.get('valor_atual'),
            abertura=abertura,
            fechamento=fechamento,
            inicio=inicio,
            status='novo'
        )
        try:
            db.session.add(novo)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            error_message = str(e.orig)
            if 'duplicate key value violates unique constraint' in error_message:
                if 'conta' in error_message:
                    flash('A conta informada já está cadastrada. Por favor, insira outra.', 'error')
                elif 'cod_bolsa' in error_message:
                    flash('O código da bolsa informado já está cadastrada. Por favor, insira outro.', 'error')
        return redirect(url_for('monitorar'))

    name = session.get('user_name')
    user_id = session.get('user_id')
    mesa = session.get('mesa')
    return render_template("cadastrar.html", name=name, user_id=user_id, mesa=mesa)


# rotas tarefas: mostram em lista tarefas do cliente, adiciona e edita tarefa e atualiza DB,
# adiciona e edita carteira do cliente
@app.route('/tarefas', methods=["POST", "GET"])
@login_required
def tarefas():
    id_do_cliente = session.get('cliente_id')
    if id_do_cliente is None:
        return "Cliente ID não encontrado na sessão", 400
    user_name = session.get('user_name')
    cliente = db.session.execute(db.select(Clientes).where(Clientes.id == id_do_cliente)).scalar()
    tarefa = db.session.execute(
        db.select(Tarefas).where(Tarefas.cliente_id == id_do_cliente, Tarefas.status != "cancelado",
                                 Tarefas.status != 'concluido', Tarefas.mesa != 1)).scalars()
    mesa = session.get('mesa')
    return render_template("tarefas.html", user_name=user_name, cliente=cliente, tarefa=tarefa, mesa=mesa)


@app.route('/adicionar_tarefa', methods=["POST", "GET"])
@login_required
def adicionar_tarefa():
    did = session.get('cliente_id')
    cliente = db.session.execute(db.select(Clientes).where(Clientes.id == did)).scalar()
    user_name = session.get('user_name')
    if request.method == "POST":
        tarefa = request.form.get('tarefa')
        tipo = request.form.get('tipo')
        prioridade = request.form.get('prioridade')
        prazo = request.form.get('prazo')
        prazo = datetime.strptime(prazo, "%Y-%m-%d").date() if prazo else None
        mesa = request.form.get('mesa')
        if mesa == 'mesa':
            mesa = 1
        else:
            mesa = 0

        novo = Tarefas(
            cliente_id=did,
            nome_cliente=cliente.nome,
            assessor_id=session.get('user_id'),
            assessor=session.get('user_name'),
            tarefa=tarefa,
            tipo=tipo,
            prioridade=prioridade,
            prazo=prazo,
            status="novo",
            mesa=mesa
        )
        db.session.add(novo)
        db.session.commit()
        return redirect(url_for('sessiondid', did=did, route='tarefas'))

    return render_template("adicionar_tarefa.html", user_name=user_name, cliente=cliente, id=did)


@app.route('/editar_tarefa', methods=["POST", "GET"])
@login_required
def editar_tarefa():
    tid = session.get('tarefa_id')
    print(tid)
    if request.method == "POST":
        prazo = request.form.get('prazo')
        prazo = datetime.strptime(prazo, "%Y-%m-%d").date() if prazo else None
        mesa = request.form.get('mesa')
        mesa = 1 if mesa == '1' else 0

        tarefa_to_update = db.session.execute(db.select(Tarefas).where(Tarefas.id == tid)).scalar()
        tarefa_to_update.tarefa = request.form.get('tarefa')
        tarefa_to_update.tipo = request.form.get('tipo')
        tarefa_to_update.prioridade = request.form.get('prioridade')
        tarefa_to_update.prazo = prazo
        tarefa_to_update.status = request.form.get('status')
        tarefa_to_update.observacao = request.form.get('observacao')
        tarefa_to_update.mesa = mesa

        try:
            db.session.commit()
            flash('Tarefa atualizada com sucesso!', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Erro ao atualizar a tarefa. Tente novamente.', 'error')

        return redirect(url_for("sessiondid", did=tarefa_to_update.cliente_id, route='tarefas'))

    user_name = session.get('user_name')
    tarefa = db.session.execute(db.select(Tarefas).where(Tarefas.id == tid)).scalar()
    print(tarefa)
    return render_template("editar_tarefa.html", tarefa=tarefa, user_name=user_name)


@app.route('/tarefas_concluidas', methods=["POST", "GET"])
@login_required
def tarefas_concluidas():
    did = session.get('cliente_id')
    user_name = session.get('user_name')
    tarefa = db.session.execute(db.select(Tarefas).where(Tarefas.cliente_id == did,
                                                         Tarefas.status == 'concluido')).scalars()
    cliente = db.session.execute(db.select(Clientes).where(Clientes.id == did)).scalar()
    return render_template("tarefas_concluidas.html", tarefa=tarefa, user_name=user_name, did=did, cliente=cliente)


@app.route("/tarefas_mesa")
@login_required
def tarefas_mesa():
    tarefas = db.session.execute(db.select(Tarefas).where(Tarefas.mesa == 1, Tarefas.status != 'concluido')).scalars()
    user_name = session.get('user_name')
    return render_template('tarefas_mesa.html', user_name=user_name, tarefas=tarefas)


@app.route("/tarefas_concluidas_mesa/")
@login_required
def tarefas_concluidas_mesa():
    tarefas = db.session.execute(db.select(Tarefas).where(Tarefas.mesa == 1, Tarefas.status == 'concluido')).scalars()
    return render_template('tarefas_concluidas_mesa.html', tarefas=tarefas)


@app.route('/editar_cliente', methods=["POST", "GET"])
@login_required
def editar_cliente():
    did = session.get('cliente_id')
    cliente = db.session.execute(db.select(Clientes).where(Clientes.id == did)).scalar()
    if request.method == "POST":
        cliente.nome = request.form['nome']
        cliente.email = request.form['email']
        cliente.telefone = request.form['telefone']
        cliente.endereco = request.form['endereco']
        cliente.conta = request.form.get('conta')
        cliente.cod_bolsa = request.form.get('cod_bolsa')
        cliente.perfil = request.form.get('perfil')
        cliente.status = request.form.get('status')
        db.session.commit()
        return redirect(url_for("sessiondid", did=did, route='tarefas'))
    user_name = session.get('user_name')
    return render_template("editar_cliente.html", cliente=cliente, user_name=user_name)


@app.route('/perfil', methods=["POST", "GET"])
@login_required
def perfil():
    user = db.session.execute(db.select(User).where(User.id == session.get('user_id'))).scalar()
    if request.method == 'POST':
        user.email = request.form['email']
        user.name = request.form['name']
        user.admin = request.form.get('admin', type=int)
        user.mesa = request.form.get('mesa', type=int)
        new_password = request.form.get('password')
        if new_password:
            user.password = generate_password_hash(new_password, method='pbkdf2:sha256', salt_length=8)
        db.session.commit()
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('perfil'))
    user_name = session.get('user_name')
    return render_template("perfil.html", user_name=user_name, user=user)


@app.route('/okr', methods=["POST", "GET"])
@login_required
def okr():
    now = datetime.now()
    current_year = now.year
    current_quarter = (now.month - 1) // 3 + 1  # Calcula o trimestre atual
    okr = db.session.execute(db.select(Okrs).where(Okrs.ano == current_year).where(Okrs.ciclo == current_quarter))
    # okr = Okrs.query.filter_by(ano=current_year, ciclo=current_quarter)
    okr = okr.scalars().all()

    ids_objs = [i.id for i in okr]
    krs = db.session.execute(db.select(Krs).where(Krs.id_obj.in_(ids_objs)))
    krs = krs.scalars().all()
    valores_atuais = [kr.atual for kr in krs]
    if len(valores_atuais) > 0:
        media_total = sum(valores_atuais) / len(valores_atuais)
    else:
        media_total = 0
    name = session.get('user_name')
    time = session.get('user_time')
    return render_template('okr.html', okr=okr, krs=krs, media_total=media_total, user_name=name, user_time=time)


@app.route("/atualizar_okr", methods=["GET", "POST"])
def atualizar_okr():
    if request.method == "POST":
        id_kr = request.form.get('kr_id')
        kr_texto = request.form.get('kr_texto')
        kr_meta = float(request.form.get('kr_meta'))
        ppp = request.form.get('ppp')
        novo_valor = float(request.form.get('novo_valor'))

        results = db.session.query(Krs).filter_by(id_kr=id_kr).first()
        results.texto = kr_texto
        results.meta = kr_meta
        results.atual = novo_valor
        db.session.commit()
        return redirect(url_for('monitorar'))
    name = session.get('user_name')
    time = session.get('user_time')
    id_kr = session.get('id_kr')
    kr = db.session.execute(db.select(Krs).where(Krs.id_kr == id_kr)).scalar()
    return render_template("atualizar_okr.html", kr=kr, user_name=name, user_time=time)


@app.route('/cadastrar_okr', methods=["POST", "GET"])
@login_required
def cadastrar_okr():
    if request.method == "POST":
        id_time = 1  # session.get('id_time')
        time = "CN Partners"  # session.get('time')
        setor = 2
        id_setor = 1
        texto = request.form['texto']
        ano = request.form['ano']
        ciclo = request.form['ciclo']
        novo = Okrs(id_time=id_time, time=time, id_setor=id_setor, setor=setor, texto=texto, ano=ano, ciclo=ciclo)
        db.session.add(novo)
        db.session.commit()
        session['id_obj'] = novo.id
        n_krs = int(request.form['n_krs'])
        return redirect(url_for('cadastrarkr', nkr=n_krs))

    user_id = session.get('user_id')
    user = db.session.execute(db.select(User).where(User.id == user_id)).scalar()
    setores = db.session.execute(db.select(Setores).where(Setores.id_time == user.id_time)).scalars()

    return render_template("cadastrarokr.html", user_name=user.name, user_time=user.time, setores=setores)


@app.route('/cadastrarkr', methods=["POST", "GET"])
@login_required
def cadastrarkr():
    if request.method == "POST":
        n_krs = int(request.form.get('n_krs'))
        for i in range(n_krs):
            tipo = request.form.get(f'tipo_{i}')
            uni_med = request.form.get(f'uni_med_{i}')
            valor_inicial = float(request.form.get(f'valor_inicial_{i}'))
            print(valor_inicial)
            valor_alterar = float(request.form.get(f'meta_{i}'))
            meta = 0
            if tipo == 1:
                if uni_med == 1:
                    meta = valor_inicial + valor_alterar
                elif uni_med == 2:
                    meta = valor_inicial * (1 + (valor_alterar / 100))
            elif tipo == 2:
                if uni_med == 1:
                    meta = valor_inicial - valor_alterar
                elif uni_med == 2:
                    meta = valor_inicial * (1 - (valor_alterar / 100))
            status = "novo"
            novo_kr = Krs(
                id_obj=session.get('id_obj'),
                texto=request.form.get(f'texto_{i}'),
                tipo=tipo,
                un_medida=uni_med,
                inicial=valor_inicial,
                valor_alterar=valor_alterar,
                meta=meta,
                status=status,
                atual=valor_inicial
            )
            db.session.add(novo_kr)
            db.session.commit()
        return redirect(url_for('okr'))

    n_krs = int(request.args.get('nkr'))
    nome = session.get('user_name')
    time = session.get('user_time')
    return render_template("cadastrarkr.html", n_krs=n_krs, nome=nome, time=time)


@app.route('/verificar_conta')
def verificar_conta():
    conta = request.args.get('conta')
    existe = Clientes.query.filter_by(conta=conta).first() is not None
    return jsonify({'exists': existe})


@app.route('/verificar_cod_bolsa')
def verificar_cod_bolsa():
    cod_bolsa = request.args.get('cod_bolsa')
    existe = Clientes.query.filter_by(cod_bolsa=cod_bolsa).first() is not None
    return jsonify({'exists': existe})


@app.route("/sessiondid/<int:did>/<route>")
@login_required
def sessiondid(did, route):
    if route == 'tarefas':
        # monitorar para tarefas
        session['cliente_id'] = did
        return redirect(url_for('tarefas'))
    elif route == 'editar_tarefa':
        # de tarefas para editar tarefa
        session['tarefa_id'] = did
        return redirect(url_for('editar_tarefa'))
    elif route == "adicionar_tarefa":
        # tarefas para adicionar tarefa
        return redirect(url_for('adicionar_tarefa'))
    elif route == 'tarefas_concluidas':
        # tarefas para tarefas concluidas
        return redirect(url_for('tarefas_concluidas'))
    elif route == 'editar_cliente':
        # de tarefas para editar cliente
        return redirect(url_for('editar_cliente'))
    elif route == 'atualizar_okr':
        session['id_kr'] = did
        return redirect(url_for('atualizar_okr'))


@app.errorhandler(401)
def unauthorized(error):
    return redirect(url_for('login'))


@app.errorhandler(404)
def unauthorized(error):
    return render_template('404.html'), 404


if __name__ == "__main__":
    app.run(debug=True)
    