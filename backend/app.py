import os
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from marshmallow import Schema, fields, ValidationError, validate
from dotenv import load_dotenv
import pymysql
import hashlib
import secrets

# Carregar variáveis de ambiente
load_dotenv()

# Configurar pymysql como MySQLdb
pymysql.install_as_MySQLdb()

# Criar aplicação Flask
app = Flask(__name__)

# ==================== CONFIGURAÇÕES ====================
class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Configuração do banco de dados
    MYSQL_HOST = os.getenv('DB_HOST', 'localhost')
    MYSQL_USER = os.getenv('DB_USER', 'root') 
    MYSQL_PASSWORD = os.getenv('DB_PASSWORD', '')
    MYSQL_DB = os.getenv('DB_NAME', 'sistema_mallory')
    MYSQL_PORT = int(os.getenv('DB_PORT', 3306))
    
    SQLALCHEMY_DATABASE_URI = (
        f"mysql://{MYSQL_USER}:{MYSQL_PASSWORD}@"
        f"{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
    )
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_timeout': 20,
        'pool_recycle': -1,
        'max_overflow': 0,
        'pool_pre_ping': True
    }
    
    # Configurações de rate limiting
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'memory://')
    
    # Configurações de logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

app.config.from_object(Config)

# ==================== EXTENSÕES ====================
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Configurar CORS corretamente
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# ==================== MODELOS ====================
class RegistroInspecao(db.Model):
    __tablename__ = 'registros_inspecao'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Dados de inspeção
    data_inspecao = db.Column(db.Date, nullable=False)
    semana = db.Column(db.String(10))
    cod_sap = db.Column(db.String(50), nullable=False, index=True)
    linha = db.Column(db.String(50))
    familia = db.Column(db.String(100))
    modelo = db.Column(db.String(100), nullable=False)
    descricao_sap = db.Column(db.Text)
    
    # Quantidades
    qtd_total = db.Column(db.Integer, default=0)
    qtd_inspecionada = db.Column(db.Integer, default=0)
    qtd_nc = db.Column(db.Integer, default=0)
    qtd_pallet = db.Column(db.Integer, default=0)
    
    # Rastreabilidade
    rastreabilidade = db.Column(db.String(100))
    po = db.Column(db.String(50))
    
    # Operação
    turno = db.Column(db.String(1))  # 'A', 'B' ou 'C'
    linha_montagem = db.Column(db.String(20))
    
    # Inspeção
    inspetor = db.Column(db.String(100), nullable=False, index=True)
    status = db.Column(db.String(20), default='pendente', index=True)
    observacao = db.Column(db.Text)
    
    # Não conformidade
    documento = db.Column(db.String(100))
    defeito = db.Column(db.String(255))
    prioridade = db.Column(db.String(20))
    origem_problema = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<RegistroInspecao {self.cod_sap} - {self.modelo}>'

class ChecklistTeste(db.Model):
    __tablename__ = 'checklist_testes'
    
    id = db.Column(db.Integer, primary_key=True)
    registro_id = db.Column(db.Integer, db.ForeignKey('registros_inspecao.id', ondelete='CASCADE'))
    
    # Testes de motor
    corrente_valor = db.Column(db.Numeric(10, 2))
    corrente_conforme = db.Column(db.Boolean)
    potencia_valor = db.Column(db.Numeric(10, 2))
    potencia_conforme = db.Column(db.Boolean)
    
    # Testes elétricos
    hipot_conforme = db.Column(db.Boolean)
    etiquetas_conforme = db.Column(db.Boolean)
    plugue_conforme = db.Column(db.Boolean)
    
    # Testes visuais
    grafismos_conforme = db.Column(db.Boolean)
    embalagens_conforme = db.Column(db.Boolean)
    pecas_injetadas_conforme = db.Column(db.Boolean)
    montagem_conforme = db.Column(db.Boolean)
    visual_conforme = db.Column(db.Boolean)
    
    # Código de barras
    codigo_barras = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamento
    registro = db.relationship('RegistroInspecao', backref='checklist_testes')

class Auditoria(db.Model):
    __tablename__ = 'auditoria'
    
    id = db.Column(db.Integer, primary_key=True)
    tabela = db.Column(db.String(50), nullable=False)
    registro_id = db.Column(db.Integer, nullable=False)
    acao = db.Column(db.Enum('INSERT', 'UPDATE', 'DELETE', name='acao_enum'), nullable=False)
    dados_anteriores = db.Column(db.JSON)
    dados_novos = db.Column(db.JSON)
    usuario = db.Column(db.String(100))
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CartaoQualidade(db.Model):
    __tablename__ = 'cartoes_qualidade'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo_produto = db.Column(db.String(50), index=True)
    nome_produto = db.Column(db.String(200), nullable=False)
    origem = db.Column(db.String(50), nullable=False)
    setor = db.Column(db.String(50), nullable=False)
    turno = db.Column(db.String(1), nullable=False)
    
    qtd_conforme = db.Column(db.Integer, default=0)
    qtd_nao_conforme = db.Column(db.Integer, default=0)
    
    status = db.Column(db.String(20), nullable=False)
    documento_reprovacao = db.Column(db.String(100))
    
    descricao = db.Column(db.Text)
    observacoes = db.Column(db.Text)
    
    responsavel = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Converter objeto para dicionário"""
        return {
            'id': self.id,
            'codigo_produto': self.codigo_produto,  # Adicionar esta linha
            'nome_produto': self.nome_produto,
            'origem': self.origem,
            'setor': self.setor,
            'turno': self.turno,
            'qtd_conforme': self.qtd_conforme,
            'qtd_nao_conforme': self.qtd_nao_conforme,
            'status': self.status,
            'documento_reprovacao': self.documento_reprovacao,
            'descricao': self.descricao,
            'observacoes': self.observacoes,
            'responsavel': self.responsavel,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    usuario = db.Column(db.String(50), unique=True, nullable=False, index=True)
    pin_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='inspetor')
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Usuario {self.usuario}>'
    
    def set_pin(self, pin):
        """Cria hash do PIN"""
        self.pin_hash = hashlib.sha256(pin.encode()).hexdigest()
    
    def verify_pin(self, pin):
        """Verifica se o PIN está correto"""
        return self.pin_hash == hashlib.sha256(pin.encode()).hexdigest()
    
    def to_dict(self):
        """Converter objeto para dicionário"""
        return {
            'id': self.id,
            'nome': self.nome,
            'usuario': self.usuario,
            'role': self.role,
            'ativo': self.ativo,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
class Produto(db.Model):
    __tablename__ = 'tb_produtos'
    
    id = db.Column(db.Integer, primary_key=True)
    cod_material = db.Column(db.String(255))
    cod_ean_upc = db.Column(db.String(255), index=True)
    cod_linha = db.Column(db.String(255))
    cod_familia = db.Column(db.String(255))
    desc_material = db.Column(db.Text)
    
    def to_dict(self):
        """Converter objeto para dicionário"""
        return {
            'id': self.id,
            'cod_material': self.cod_material,
            'cod_ean_upc': self.cod_ean_upc,
            'cod_linha': self.cod_linha,
            'cod_familia': self.cod_familia,
            'desc_material': self.desc_material
        }

# ==================== SCHEMAS DE VALIDAÇÃO ====================
class RegistroInspecaoSchema(Schema):
    id = fields.Int(dump_only=True)
    data_inspecao = fields.Date(required=True)
    semana = fields.Str(validate=validate.Length(max=10))
    cod_sap = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    linha = fields.Str(validate=validate.Length(max=50))
    familia = fields.Str(validate=validate.Length(max=100))
    modelo = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    descricao_sap = fields.Str()
    
    qtd_total = fields.Int(validate=validate.Range(min=0), load_default=0)
    qtd_inspecionada = fields.Int(validate=validate.Range(min=0), load_default=0)
    qtd_nc = fields.Int(validate=validate.Range(min=0), load_default=0)
    qtd_pallet = fields.Int(validate=validate.Range(min=0), load_default=0)
    
    rastreabilidade = fields.Str(validate=validate.Length(max=100))
    po = fields.Str(validate=validate.Length(max=50))
    
    turno = fields.Str(validate=validate.OneOf(['A', 'B', 'C']))
    linha_montagem = fields.Str(validate=validate.Length(max=20))
    
    inspetor = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    status = fields.Str(validate=validate.OneOf(['pendente', 'aprovado', 'reprovado']), load_default='pendente')
    observacao = fields.Str()
    
    documento = fields.Str(validate=validate.Length(max=100))
    defeito = fields.Str(validate=validate.Length(max=255))
    prioridade = fields.Str(validate=validate.OneOf(['critico', 'primario', 'secundario']))
    origem_problema = fields.Str()
    
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class CartaoQualidadeSchema(Schema):
    id = fields.Int(dump_only=True)
    codigo_produto = fields.Str(allow_none=True)  # Adicionar esta linha
    nome_produto = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    origem = fields.Str(required=True, validate=validate.OneOf(['nacional', 'importado', 'Nacional', 'Importado']))
    setor = fields.Str(required=True, validate=validate.Length(max=50))
    turno = fields.Str(required=True, validate=validate.OneOf(['A', 'B', 'C']))
    
    qtd_conforme = fields.Int(validate=validate.Range(min=0), load_default=0)
    qtd_nao_conforme = fields.Int(validate=validate.Range(min=0), load_default=0)
    
    status = fields.Str(required=True, validate=validate.OneOf(['aprovado', 'reprovado', 'Aprovado', 'Reprovado']))
    documento_reprovacao = fields.Str(validate=validate.Length(max=100))
    
    descricao = fields.Str()
    observacoes = fields.Str()
    
    responsavel = fields.Str(validate=validate.Length(max=100))
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

# Instancias dos schemas
registro_schema = RegistroInspecaoSchema()
registros_schema = RegistroInspecaoSchema(many=True)
cartao_schema = CartaoQualidadeSchema()
cartoes_schema = CartaoQualidadeSchema(many=True)

# ==================== UTILITÁRIOS ====================
def create_response(success=True, message="", data=None, errors=None, status_code=200):
    """Criar resposta padronizada da API"""
    response = {
        "success": success,
        "message": message
    }
    
    if data is not None:
        response["data"] = data
        
    if errors is not None:
        response["errors"] = errors
    
    return jsonify(response), status_code

def log_audit(tabela, registro_id, acao, dados_anteriores=None, dados_novos=None):
    """Registrar ação na auditoria"""
    try:
        auditoria = Auditoria(
            tabela=tabela,
            registro_id=registro_id,
            acao=acao,
            dados_anteriores=dados_anteriores,
            dados_novos=dados_novos,
            usuario=request.headers.get('X-User', 'sistema'),
            ip_address=request.remote_addr
        )
        db.session.add(auditoria)
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Erro ao registrar auditoria: {str(e)}")

# ==================== MIDDLEWARE DE ERRO ====================
@app.errorhandler(ValidationError)
def handle_validation_error(e):
    return create_response(
        success=False,
        message="Dados inválidos",
        errors=e.messages,
        status_code=400
    )

@app.errorhandler(404)
def handle_not_found(e):
    return create_response(
        success=False,
        message="Recurso não encontrado",
        status_code=404
    )

@app.errorhandler(500)
def handle_internal_error(e):
    db.session.rollback()
    app.logger.error(f"Erro interno: {str(e)}")
    return create_response(
        success=False,
        message="Erro interno do servidor",
        status_code=500
    )

# ==================== ROUTES - REGISTROS ====================
@app.route('/api/registros', methods=['GET', 'POST', 'OPTIONS'])
@limiter.limit("100 per minute")
def handle_registros():
    """Listar e criar registros"""
    if request.method == 'OPTIONS':
        return '', 200
    
    if request.method == 'GET':
        try:
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('limit', 50, type=int), 100)
            search = request.args.get('search', '')
            status = request.args.get('status', '')
            
            query = RegistroInspecao.query
            
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    db.or_(
                        RegistroInspecao.cod_sap.like(search_pattern),
                        RegistroInspecao.modelo.like(search_pattern),
                        RegistroInspecao.inspetor.like(search_pattern)
                    )
                )
            
            if status:
                query = query.filter(RegistroInspecao.status == status)
            
            query = query.order_by(RegistroInspecao.data_inspecao.desc(), RegistroInspecao.id.desc())
            paginated = query.paginate(page=page, per_page=per_page, error_out=False)
            
            registros_data = registros_schema.dump(paginated.items)
            
            return create_response(
                success=True,
                data=registros_data,
                message=f"Encontrados {paginated.total} registros"
            )
            
        except Exception as e:
            app.logger.error(f"Erro ao buscar registros: {str(e)}")
            return create_response(
                success=False,
                message="Erro ao buscar registros",
                status_code=500
            )
    
    # POST - Criar novo registro
    if request.method == 'POST':
        try:
            dados = request.get_json()
            print(f"Dados recebidos: {dados}")
            
            # Criar novo registro
            novo_registro = RegistroInspecao(
                data_inspecao=datetime.strptime(dados.get('data_inspecao'), '%Y-%m-%d').date() if dados.get('data_inspecao') else datetime.now().date(),
                semana=dados.get('semana'),
                cod_sap=dados.get('cod_sap'),
                linha=dados.get('linha'),
                familia=dados.get('familia'),
                modelo=dados.get('modelo'),
                descricao_sap=dados.get('descricao_sap'),
                qtd_total=int(dados.get('qtd_total', 0)),
                qtd_inspecionada=int(dados.get('qtd_inspecionada', 0)),
                qtd_nc=int(dados.get('qtd_nc', 0)),
                qtd_pallet=int(dados.get('qtd_pallet', 0)),
                rastreabilidade=dados.get('rastreabilidade'),
                po=dados.get('po'),
                turno=dados.get('turno'),
                linha_montagem=dados.get('linha_montagem'),
                inspetor=dados.get('inspetor', 'Sistema'),
                status=dados.get('status', 'pendente'),
                observacao=dados.get('observacao'),
                documento=dados.get('documento'),
                defeito=dados.get('defeito'),
                prioridade=dados.get('prioridade'),
                origem_problema=dados.get('origem_problema')
            )
            
            db.session.add(novo_registro)
            db.session.commit()
            
            print(f"Registro salvo com ID: {novo_registro.id}")
            
            return create_response(
                success=True,
                message='Registro criado com sucesso',
                data=registro_schema.dump(novo_registro),
                status_code=201
            )
            
        except Exception as e:
            print(f"ERRO: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return create_response(
                success=False,
                message=f'Erro ao criar registro: {str(e)}',
                status_code=400
            )

@app.route('/api/registros/<int:id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'])
def handle_registro_individual(id):
    """GET, PUT ou DELETE em registro específico"""
    
    if request.method == 'OPTIONS':
        return '', 200
    
    # GET - Buscar registro
    if request.method == 'GET':
        try:
            registro = RegistroInspecao.query.get(id)
            
            if not registro:
                return create_response(
                    success=False,
                    message=f"Registro {id} não encontrado",
                    status_code=404
                )
            
            return create_response(
                success=True,
                data=registro_schema.dump(registro)
            )
            
        except Exception as e:
            app.logger.error(f"Erro ao buscar registro {id}: {str(e)}")
            return create_response(
                success=False,
                message=f"Erro: {str(e)}",
                status_code=500
            )
    
    # PUT - Atualizar registro
    elif request.method == 'PUT':
        try:
            registro = RegistroInspecao.query.get(id)
            
            if not registro:
                return create_response(
                    success=False,
                    message=f"Registro {id} não encontrado",
                    status_code=404
                )
            
            dados = request.get_json()
            
            # Atualizar data
            if 'data_inspecao' in dados and dados['data_inspecao']:
                if isinstance(dados['data_inspecao'], str):
                    registro.data_inspecao = datetime.strptime(dados['data_inspecao'], '%Y-%m-%d').date()
            
            # Atualizar outros campos
            campos = ['semana', 'cod_sap', 'linha', 'familia', 'modelo', 'descricao_sap',
                     'qtd_total', 'qtd_inspecionada', 'qtd_nc', 'qtd_pallet',
                     'rastreabilidade', 'po', 'turno', 'linha_montagem', 'inspetor',
                     'status', 'observacao', 'documento', 'defeito', 'prioridade', 
                     'origem_problema']
            
            for campo in campos:
                if campo in dados:
                    setattr(registro, campo, dados[campo])
            
            registro.updated_at = datetime.utcnow()
            db.session.commit()
            
            print(f"Registro {id} atualizado com sucesso")
            
            return create_response(
                success=True,
                message="Registro atualizado com sucesso",
                data=registro_schema.dump(registro)
            )
            
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao atualizar: {str(e)}")
            import traceback
            traceback.print_exc()
            return create_response(
                success=False,
                message=f"Erro: {str(e)}",
                status_code=500
            )
    
    # DELETE - Excluir registro
    elif request.method == 'DELETE':
        try:
            print(f"\n{'='*60}")
            print(f"DELETANDO REGISTRO ID: {id}")
            print(f"{'='*60}")
            
            # Buscar registro
            registro = RegistroInspecao.query.get(id)
            
            if not registro:
                print(f"Registro {id} NAO ENCONTRADO")
                return create_response(
                    success=False,
                    message=f"Registro {id} não encontrado",
                    status_code=404
                )
            
            print(f"Registro encontrado: {registro.cod_sap} - {registro.modelo}")
            
            # Contar antes
            total_antes = RegistroInspecao.query.count()
            print(f"Total ANTES da exclusão: {total_antes}")
            
            # Deletar
            db.session.delete(registro)
            db.session.flush()  # Força execução imediata
            db.session.commit()
            
            # Contar depois
            total_depois = RegistroInspecao.query.count()
            print(f"Total DEPOIS da exclusão: {total_depois}")
            
            # Verificar
            verificacao = RegistroInspecao.query.get(id)
            
            if verificacao is None:
                print(f"SUCESSO! Registro {id} FOI DELETADO DO BANCO!")
                print(f"{'='*60}\n")
                
                return create_response(
                    success=True,
                    message="Registro excluído com sucesso"
                )
            else:
                print(f"FALHOU! Registro {id} AINDA EXISTE!")
                print(f"{'='*60}\n")
                db.session.rollback()
                return create_response(
                    success=False,
                    message="Falha ao excluir registro",
                    status_code=500
                )
                
        except Exception as e:
            db.session.rollback()
            print(f"ERRO: {str(e)}")
            import traceback
            traceback.print_exc()
            print(f"{'='*60}\n")
            return create_response(
                success=False,
                message=f"Erro ao excluir: {str(e)}",
                status_code=500
            )

# ==================== ROUTES - DASHBOARD ====================
@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Estatísticas para dashboard"""
    try:
        total_registros = RegistroInspecao.query.count()
        
        status_stats = db.session.query(
            RegistroInspecao.status,
            db.func.count(RegistroInspecao.id).label('count')
        ).group_by(RegistroInspecao.status).all()
        
        status_distribution = [
            {'status': stat.status, 'count': stat.count}
            for stat in status_stats
        ]
        
        hoje = datetime.now().date()
        primeiro_dia_mes = hoje.replace(day=1)
        registros_mes = RegistroInspecao.query.filter(
            RegistroInspecao.data_inspecao >= primeiro_dia_mes
        ).count()
        
        top_inspetores = db.session.query(
            RegistroInspecao.inspetor,
            db.func.count(RegistroInspecao.id).label('total_inspecoes')
        ).group_by(RegistroInspecao.inspetor)\
         .order_by(db.func.count(RegistroInspecao.id).desc())\
         .limit(5).all()
        
        inspetores_data = [
            {'inspetor': insp.inspetor, 'total_inspecoes': insp.total_inspecoes}
            for insp in top_inspetores
        ]
        
        data_limite = hoje - timedelta(days=30)
        registros_por_dia = db.session.query(
            RegistroInspecao.data_inspecao,
            db.func.count(RegistroInspecao.id).label('total')
        ).filter(RegistroInspecao.data_inspecao >= data_limite)\
         .group_by(RegistroInspecao.data_inspecao)\
         .order_by(RegistroInspecao.data_inspecao).all()
        
        registros_diarios = [
            {'data': reg.data_inspecao.isoformat(), 'total': reg.total}
            for reg in registros_por_dia
        ]
        
        stats_data = {
            'total_registros': total_registros,
            'registros_mes': registros_mes,
            'status_distribution': status_distribution,
            'top_inspetores': inspetores_data,
            'registros_por_dia': registros_diarios
        }
        
        return create_response(
            success=True,
            data=stats_data
        )
        
    except Exception as e:
        app.logger.error(f"Erro ao buscar estatísticas: {str(e)}")
        return create_response(
            success=False,
            message="Erro ao buscar estatísticas",
            status_code=500
        )

@app.route('/api/dashboard/inspecoes-por-linha', methods=['GET'])
def get_inspecoes_por_linha():
    """Inspeções agrupadas por linha de montagem"""
    try:
        linhas_stats = db.session.query(
            RegistroInspecao.linha_montagem,
            db.func.count(RegistroInspecao.id).label('total'),
            db.func.count(db.case([(RegistroInspecao.status == 'aprovado', 1)])).label('aprovados'),
            db.func.count(db.case([(RegistroInspecao.status == 'reprovado', 1)])).label('reprovados')
        ).filter(RegistroInspecao.linha_montagem.isnot(None))\
         .group_by(RegistroInspecao.linha_montagem)\
         .order_by(db.func.count(RegistroInspecao.id).desc())\
         .all()
        
        linhas_data = [{
            'linha': linha.linha_montagem,
            'total': linha.total,
            'aprovados': linha.aprovados,
            'reprovados': linha.reprovados,
            'taxa_aprovacao': round((linha.aprovados / linha.total) * 100, 1) if linha.total > 0 else 0
        } for linha in linhas_stats]
        
        return create_response(
            success=True, 
            data=linhas_data,
            message=f"Dados recuperados com sucesso para {len(linhas_data)} linhas"
        )
        
    except Exception as e:
        app.logger.error(f"Erro ao buscar inspeções por linha: {str(e)}")
        return create_response(
            success=False, 
            message="Erro ao buscar dados de inspeções por linha",
            status_code=500
        )

# ==================== ROUTES - CARTÕES DE QUALIDADE ====================
@app.route('/api/cartoes', methods=['GET', 'POST', 'OPTIONS'])
@limiter.limit("100 per minute")
def handle_cartoes():
    """Listar e criar cartões de qualidade"""
    
    if request.method == 'OPTIONS':
        return '', 200
    
    if request.method == 'GET':
        try:
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('limit', 50, type=int), 100)
            search = request.args.get('search', '')
            status = request.args.get('status', '')
            
            query = CartaoQualidade.query
            
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    db.or_(
                        CartaoQualidade.nome_produto.like(search_pattern),
                        CartaoQualidade.descricao.like(search_pattern),
                        CartaoQualidade.origem.like(search_pattern),
                        CartaoQualidade.setor.like(search_pattern)
                    )
                )
            
            if status:
                query = query.filter(CartaoQualidade.status == status)
            
            query = query.order_by(CartaoQualidade.created_at.desc())
            
            if page == 1 and not request.args.get('page'):
                cartoes = query.all()
                total = len(cartoes)
            else:
                paginated = query.paginate(page=page, per_page=per_page, error_out=False)
                cartoes = paginated.items
                total = paginated.total
            
            cartoes_data = [cartao.to_dict() for cartao in cartoes]
            
            return create_response(
                success=True,
                data=cartoes_data,
                message=f"Encontrados {total} cartões"
            )
            
        except Exception as e:
            app.logger.error(f"Erro ao buscar cartões: {str(e)}")
            import traceback
            traceback.print_exc()
            return create_response(
                success=False,
                message=f"Erro ao buscar cartões: {str(e)}",
                status_code=500
            )
    
    if request.method == 'POST':
        try:
            dados = request.get_json()
            
            campos_obrigatorios = [ 'origem', 'setor', 'turno', 'status']
            for campo in campos_obrigatorios:
                if not dados.get(campo):
                    return create_response(
                        success=False,
                        message=f"Campo obrigatório ausente: {campo}",
                        status_code=400
                    )
            codigo_produto = dados.get('codigo_produto', '').strip()
            nome_produto = dados.get('nome_produto', '').strip()
                
            # Se não tiver nome, usar código
            if not nome_produto:
                nome_produto = codigo_produto
            
            novo_cartao = CartaoQualidade(
                codigo_produto=codigo_produto,
                nome_produto=nome_produto,
                origem=dados['origem'],
                setor=dados['setor'],
                turno=dados['turno'],
                qtd_conforme=int(dados.get('qtd_conforme', 0)),
                qtd_nao_conforme=int(dados.get('qtd_nao_conforme', 0)),
                status=dados['status'],
                documento_reprovacao=dados.get('documento_reprovacao', ''),
                descricao=dados.get('descricao', ''),
                observacoes=dados.get('observacoes', ''),
                responsavel=dados.get('responsavel', 'Usuario')
            )
            
            db.session.add(novo_cartao)
            db.session.commit()
            
            return create_response(
                success=True,
                data=novo_cartao.to_dict(),
                message="Cartão criado com sucesso",
                status_code=201
            )
            
        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return create_response(
                success=False,
                message=f"Erro ao criar cartão: {str(e)}",
                status_code=400
            )

@app.route('/api/cartoes/<int:id>', methods=['GET'])
def get_cartao(id):
    try:
        cartao = CartaoQualidade.query.get(id)
        print("Dados do cartão:", cartao.to_dict())  # Log para debug
        return create_response(
            success=True,
            data=cartao.to_dict()
        )
    except Exception as e:
        app.logger.error(f"Erro ao buscar cartão {id}: {str(e)}")
        return create_response(
            success=False,
            message=f"Erro: {str(e)}",
            status_code=500
        )

@app.route('/api/cartoes/<int:id>', methods=['PUT', 'DELETE', 'OPTIONS'])
@limiter.limit("50 per minute")
def handle_cartao(id):
    """Buscar, atualizar ou excluir cartão específico"""
    
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        cartao = CartaoQualidade.query.get(id)
        
        if not cartao:
            return create_response(
                success=False,
                message=f"Cartão com ID {id} não encontrado",
                status_code=404
            )
        
        if request.method == 'GET':
            return create_response(
                success=True,
                data=cartao.to_dict()
            )
            
        elif request.method == 'PUT':
            try:
                dados = request.get_json()
                
                campos_obrigatorios = ['nome_produto', 'origem', 'setor', 'turno', 'status']
                for campo in campos_obrigatorios:
                    if not dados.get(campo):
                        return create_response(
                            success=False,
                            message=f"Campo obrigatório ausente: {campo}",
                            status_code=400
                        )
                
                cartao.nome_produto = dados['nome_produto']
                cartao.origem = dados['origem']
                cartao.setor = dados['setor']
                cartao.turno = dados['turno']
                cartao.qtd_conforme = int(dados.get('qtd_conforme', 0))
                cartao.qtd_nao_conforme = int(dados.get('qtd_nao_conforme', 0))
                cartao.status = dados['status']
                cartao.documento_reprovacao = dados.get('documento_reprovacao', '')
                cartao.descricao = dados.get('descricao', '')
                cartao.observacoes = dados.get('observacoes', '')
                cartao.responsavel = dados.get('responsavel', cartao.responsavel)
                cartao.updated_at = datetime.utcnow()
                
                db.session.commit()
                
                return create_response(
                    success=True,
                    message="Cartão atualizado com sucesso",
                    data=cartao.to_dict()
                )
                
            except Exception as e:
                db.session.rollback()
                import traceback
                traceback.print_exc()
                return create_response(
                    success=False,
                    message=f"Erro ao atualizar cartão: {str(e)}",
                    status_code=400
                )
            
        elif request.method == 'DELETE':
            try:
                db.session.delete(cartao)
                db.session.commit()
                
                return create_response(
                    success=True,
                    message="Cartão excluído com sucesso"
                )
                
            except Exception as e:
                db.session.rollback()
                import traceback
                traceback.print_exc()
                return create_response(
                    success=False,
                    message=f"Erro ao excluir cartão: {str(e)}",
                    status_code=500
                )
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return create_response(
            success=False,
            message=f"Erro ao processar cartão: {str(e)}",
            status_code=500
        )

@app.route('/api/cartoes/stats', methods=['GET'])
def get_cartoes_stats():
    """Estatísticas dos cartões de qualidade"""
    try:
        total = CartaoQualidade.query.count()
        aprovados = CartaoQualidade.query.filter_by(status='Aprovado').count()
        reprovados = CartaoQualidade.query.filter_by(status='Reprovado').count()
        
        por_setor = db.session.query(
            CartaoQualidade.setor,
            db.func.count(CartaoQualidade.id).label('total')
        ).group_by(CartaoQualidade.setor).all()
        
        stats = {
            'total': total,
            'aprovados': aprovados,
            'reprovados': reprovados,
            'taxa_aprovacao': round((aprovados / total * 100), 1) if total > 0 else 0,
            'por_setor': [{'setor': s.setor, 'total': s.total} for s in por_setor]
        }
        
        return create_response(
            success=True,
            data=stats
        )
    except Exception as e:
        app.logger.error(f"Erro ao buscar estatísticas: {str(e)}")
        return create_response(
            success=False,
            message="Erro ao buscar estatísticas",
            status_code=500
        )

# ==================== ROUTES - AUTENTICAÇÃO ====================
@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def login():
    """Login de usuário"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        dados = request.get_json()
        usuario = dados.get('usuario')
        pin = dados.get('pin')
        
        if not usuario or not pin:
            return create_response(
                success=False,
                message='Usuário e PIN são obrigatórios',
                status_code=400
            )
        
        if len(pin) != 4 or not pin.isdigit():
            return create_response(
                success=False,
                message='PIN deve ter 4 dígitos',
                status_code=400
            )
        
        # Buscar usuário
        user = Usuario.query.filter_by(usuario=usuario, ativo=True).first()
        
        if not user or not user.verify_pin(pin):
            return create_response(
                success=False,
                message='Usuário ou PIN inválido',
                status_code=401
            )
        
        # Gerar token simples (em produção, use JWT)
        token = secrets.token_hex(32)
        
        # Log de auditoria
        try:
            log_audit('usuarios', user.id, 'LOGIN', 
                     dados_novos={'usuario': user.usuario, 'timestamp': datetime.utcnow().isoformat()})
        except Exception:
            pass
        
        return create_response(
            success=True,
            message='Login realizado com sucesso',
            data={
                'token': token,
                'usuario': user.to_dict()
            }
        )
        
    except Exception as e:
        print(f"Erro no login: {str(e)}")
        import traceback
        traceback.print_exc()
        return create_response(
            success=False,
            message='Erro ao fazer login',
            status_code=500
        )

@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
def register():
    """Registrar novo usuário"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        dados = request.get_json()
        
        # Validar campos obrigatórios
        if not dados.get('nome') or not dados.get('usuario') or not dados.get('pin'):
            return create_response(
                success=False,
                message='Nome, usuário e PIN são obrigatórios',
                status_code=400
            )
        
        # Validar PIN
        pin = dados.get('pin')
        if len(pin) != 4 or not pin.isdigit():
            return create_response(
                success=False,
                message='PIN deve ter 4 dígitos',
                status_code=400
            )
        
        # Verificar se usuário já existe
        usuario_existente = Usuario.query.filter_by(usuario=dados.get('usuario')).first()
        if usuario_existente:
            return create_response(
                success=False,
                message='Usuário já existe',
                status_code=409
            )
        
        # Criar novo usuário
        novo_usuario = Usuario(
            nome=dados.get('nome'),
            usuario=dados.get('usuario'),
            role=dados.get('role', 'inspetor')
        )
        novo_usuario.set_pin(pin)
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        return create_response(
            success=True,
            message='Usuário criado com sucesso',
            data=novo_usuario.to_dict(),
            status_code=201
        )
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao registrar usuário: {str(e)}")
        import traceback
        traceback.print_exc()
        return create_response(
            success=False,
            message='Erro ao criar usuário',
            status_code=500
        )

@app.route('/api/auth/verify-admin', methods=['POST', 'OPTIONS'])
def verify_admin():
    """Verificar PIN de administrador"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        dados = request.get_json()
        pin = dados.get('pin')
        
        if not pin or len(pin) != 4:
            return create_response(
                success=False,
                message='PIN inválido',
                status_code=400
            )
        
        # Buscar administrador com o PIN (pode ter vários admins)
        admins = Usuario.query.filter_by(role='admin', ativo=True).all()
        
        for admin in admins:
            if admin.verify_pin(pin):
                return create_response(
                    success=True,
                    message='Verificação bem-sucedida',
                    data={'admin_id': admin.id, 'admin_nome': admin.nome}
                )
        
        return create_response(
            success=False,
            message='PIN de administrador inválido',
            status_code=401
        )
        
    except Exception as e:
        print(f"Erro ao verificar admin: {str(e)}")
        return create_response(
            success=False,
            message='Erro na verificação',
            status_code=500
        )

@app.route('/api/auth/usuarios', methods=['GET', 'OPTIONS'])
def listar_usuarios():
    """Listar todos os usuários (apenas admin)"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        usuarios = Usuario.query.filter_by(ativo=True).all()
        usuarios_data = [user.to_dict() for user in usuarios]
        
        return create_response(
            success=True,
            data=usuarios_data
        )
        
    except Exception as e:
        print(f"Erro ao listar usuários: {str(e)}")
        return create_response(
            success=False,
            message='Erro ao buscar usuários',
            status_code=500
        )

@app.route('/api/auth/usuarios/<int:id>', methods=['DELETE', 'OPTIONS'])
def deletar_usuario(id):
    """Desativar usuário (soft delete)"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        usuario = Usuario.query.get(id)
        
        if not usuario:
            return create_response(
                success=False,
                message='Usuário não encontrado',
                status_code=404
            )
        
        # Soft delete
        usuario.ativo = False
        db.session.commit()
        
        return create_response(
            success=True,
            message='Usuário desativado com sucesso'
        )
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao desativar usuário: {str(e)}")
        return create_response(
            success=False,
            message='Erro ao desativar usuário',
            status_code=500
        )
        
@app.route('/api/produtos', methods=['GET', 'OPTIONS'])
@limiter.limit("200 per minute")
def listar_produtos():
    """Listar todos os produtos"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Buscar todos os produtos
        produtos = Produto.query.all()
        
        produtos_data = [produto.to_dict() for produto in produtos]
        
        return create_response(
            success=True,
            data=produtos_data,
            message=f"Encontrados {len(produtos_data)} produtos"
        )
        
    except Exception as e:
        app.logger.error(f"Erro ao buscar produtos: {str(e)}")
        import traceback
        traceback.print_exc()
        return create_response(
            success=False,
            message=f"Erro ao buscar produtos: {str(e)}",
            status_code=500
        )


@app.route('/api/produtos/<codigo>', methods=['GET', 'OPTIONS'])
@limiter.limit("100 per minute")
def buscar_produto_por_codigo(codigo):
    """Busca produto por código SAP"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        print(f"🔍 Buscando produto com código: {codigo}")
        
        # Buscar por código do material
        produto = Produto.query.filter_by(cod_material=codigo).first()
        
        if produto:
            print(f"✅ Produto encontrado: {produto.desc_material}")
            return create_response(
                success=True,
                data=produto.to_dict()
            )
        else:
            print(f"❌ Produto não encontrado")
            return create_response(
                success=False,
                message='Produto não encontrado',
                status_code=404
            )
        
    except Exception as e:
        app.logger.error(f"Erro ao buscar produto: {str(e)}")
        import traceback
        traceback.print_exc()
        return create_response(
            success=False,
            message=f"Erro ao buscar produto: {str(e)}",
            status_code=500
        )


@app.route('/api/produtos/barcode/<codigo_barras>', methods=['GET', 'OPTIONS'])
@limiter.limit("100 per minute")
def buscar_produto_por_barcode(codigo_barras):
    """Busca produto por código de barras (EAN/UPC)"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        print(f"📊 Buscando produto com código de barras: {codigo_barras}")
        
        # Buscar por código EAN/UPC
        produto = Produto.query.filter_by(cod_ean_upc=codigo_barras).first()
        
        if produto:
            print(f"✅ Produto encontrado: {produto.desc_material}")
            return create_response(
                success=True,
                data=produto.to_dict()
            )
        else:
            print(f"❌ Produto não encontrado com código de barras")
            return create_response(
                success=False,
                message='Produto não encontrado',
                status_code=404
            )
        
    except Exception as e:
        app.logger.error(f"Erro ao buscar produto por código de barras: {str(e)}")
        import traceback
        traceback.print_exc()
        return create_response(
            success=False,
            message=f"Erro ao buscar produto: {str(e)}",
            status_code=500
        )


@app.route('/api/produtos/search', methods=['GET'])
@limiter.limit("100 per minute")
def search_produtos():
    try:
        termo = request.args.get('q', '').strip().upper()
        
        if not termo or len(termo) < 2:
            return create_response(
                success=False,
                message='Termo de busca deve ter pelo menos 2 caracteres',
                status_code=400
            )
        
        # Buscar produtos que correspondam ao termo
        produtos = Produto.query.filter(
            db.or_(
                Produto.cod_material.like(f"{termo}%"),
                db.func.upper(Produto.desc_material).like(f"%{termo}%")
            )
        ).order_by(Produto.cod_material).limit(10).all()
        
        produtos_data = [produto.to_dict() for produto in produtos]
        
        return create_response(
            success=True,
            data=produtos_data,
            message=f"Encontrados {len(produtos_data)} produtos"
        )
        
    except Exception as e:
        app.logger.error(f"Erro na busca de produtos: {str(e)}")
        return create_response(
            success=False,
            message=f"Erro na busca: {str(e)}",
            status_code=500
        )

# ==================== HEALTH CHECK ====================
@app.route('/api/health', methods=['GET'])
def health_check():
    """Verificar saúde da aplicação"""
    try:
        db.session.execute(db.text('SELECT 1'))
        
        return create_response(
            success=True,
            message="Servidor e banco de dados funcionando",
            data={
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
                'database': 'connected'
            }
        )
    except Exception as e:
        app.logger.error(f"Health check failed: {str(e)}")
        return create_response(
            success=False,
            message="Erro na conexão com banco de dados",
            data={
                'timestamp': datetime.utcnow().isoformat(),
                'database': 'disconnected',
                'error': str(e)
            },
            status_code=503
        )

# ==================== FUNÇÃO PARA CRIAR ADMIN PADRÃO ====================
def criar_admin_padrao():
    """Criar administrador padrão se não existir"""
    with app.app_context():
        admin = Usuario.query.filter_by(usuario='admin').first()
        
        if not admin:
            admin = Usuario(
                nome='Administrador',
                usuario='admin',
                role='admin'
            )
            admin.set_pin('1234')  # PIN padrão: 1234
            
            db.session.add(admin)
            db.session.commit()
            
            print("=" * 60)
            print("👤 ADMINISTRADOR PADRÃO CRIADO")
            print("=" * 60)
            print("Usuário: admin")
            print("PIN: 1234")
            print("⚠️  IMPORTANTE: Altere o PIN após o primeiro login!")
            print("=" * 60)

# ==================== INICIALIZAÇÃO ====================
if __name__ == '__main__':
    print("="*60)
    print("Iniciando Sistema MALLORY")
    print("Banco de dados: sistema_mallory")
    print("Servidor: http://localhost:5000")
    print("="*60)
    
    # Criar tabelas e admin padrão
    with app.app_context():
        db.create_all()
        criar_admin_padrao()
    
    app.run(host='0.0.0.0', port=5000, debug=True)