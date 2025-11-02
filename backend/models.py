from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event

db = SQLAlchemy()

class RegistroInspecao(db.Model):
    __tablename__ = 'registros_inspecao'
    
    # Configurações da tabela
    __table_args__ = (
        db.Index('idx_data_status', 'data_inspecao', 'status'),
        db.Index('idx_cod_sap_modelo', 'cod_sap', 'modelo'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Dados de inspeção
    data_inspecao = db.Column(db.Date, nullable=False, index=True)
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
    turno = db.Column(db.Enum('A', 'B', 'C', name='turno_enum'))
    linha_montagem = db.Column(db.String(20))
    
    # Inspeção
    inspetor = db.Column(db.String(100), nullable=False, index=True)
    status = db.Column(db.Enum('pendente', 'aprovado', 'reprovado', name='status_enum'), 
                      default='pendente', index=True)
    observacao = db.Column(db.Text)
    
    # Não conformidade (quando status = reprovado)
    documento = db.Column(db.String(100))
    defeito = db.Column(db.String(255))
    prioridade = db.Column(db.Enum('critico', 'primario', 'secundario', name='prioridade_enum'))
    origem_problema = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Converter para dicionário"""
        return {
            'id': self.id,
            'data_inspecao': self.data_inspecao.isoformat() if self.data_inspecao else None,
            'semana': self.semana,
            'cod_sap': self.cod_sap,
            'linha': self.linha,
            'familia': self.familia,
            'modelo': self.modelo,
            'descricao_sap': self.descricao_sap,
            'qtd_total': self.qtd_total,
            'qtd_inspecionada': self.qtd_inspecionada,
            'qtd_nc': self.qtd_nc,
            'qtd_pallet': self.qtd_pallet,
            'rastreabilidade': self.rastreabilidade,
            'po': self.po,
            'turno': self.turno,
            'linha_montagem': self.linha_montagem,
            'inspetor': self.inspetor,
            'status': self.status,
            'observacao': self.observacao,
            'documento': self.documento,
            'defeito': self.defeito,
            'prioridade': self.prioridade,
            'origem_problema': self.origem_problema,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<RegistroInspecao {self.cod_sap} - {self.modelo}>'

# Event listeners para auditoria automática
@event.listens_for(RegistroInspecao, 'after_insert')
def log_insert(mapper, connection, target):
    """Log de inserção automático"""
    pass  # Implementar se necessário

