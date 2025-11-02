#!/usr/bin/env python3
"""
Script de migração do banco de dados
"""

from flask import Flask
from flask_migrate import Migrate, init, migrate, upgrade
from app import app, db
import os

def init_db():
    """Inicializar migrações"""
    if not os.path.exists('migrations'):
        init()
        print("✅ Migrations inicializadas")
    else:
        print("ℹ️  Migrations já existem")

def create_migration(message="Auto migration"):
    """Criar nova migração"""
    migrate(message=message)
    print(f"✅ Migração criada: {message}")

def apply_migrations():
    """Aplicar migrações pendentes"""
    upgrade()
    print("✅ Migrações aplicadas")

def setup_database():
    """Setup completo do banco"""
    with app.app_context():
        # Criar tabelas se não existirem
        db.create_all()
        print("✅ Tabelas criadas/verificadas")
        
        # Inserir dados de teste (opcional)
        insert_sample_data()

def insert_sample_data():
    """Inserir dados de exemplo para teste"""
    from models import RegistroInspecao
    from datetime import date
    
    # Verificar se já existem dados
    if RegistroInspecao.query.count() > 0:
        print("ℹ️  Dados já existem no banco")
        return
    
    # Dados de exemplo
    registros_exemplo = [
        {
            'data_inspecao': date(2025, 12, 26),
            'semana': '52',
            'cod_sap': 'B94401022',
            'linha': 'Ventilador',
            'familia': 'Mesa',
            'modelo': 'Turbo Fresh 40cm',
            'descricao_sap': 'Ventilador de Mesa 40cm Preto',
            'qtd_total': 30,
            'qtd_inspecionada': 6,
            'qtd_nc': 1,
            'rastreabilidade': '255231TX',
            'po': 'PO-9876',
            'qtd_pallet': 2,
            'turno': 'A',
            'linha_montagem': 'LM-03',
            'inspetor': 'Carlos Souza',
            'status': 'pendente',
            'observacao': 'Inspeção inicial realizada'
        },
        {
            'data_inspecao': date(2025, 12, 25),
            'semana': '52',
            'cod_sap': 'B944000992',
            'linha': 'Ventilador',
            'familia': 'Coluna',
            'modelo': 'Coluna',
            'descricao_sap': 'Ventilador de Coluna 40cm Air Timer',
            'qtd_total': 30,
            'qtd_inspecionada': 6,
            'qtd_nc': 0,
            'rastreabilidade': '255232TX',
            'po': 'PO-9875',
            'qtd_pallet': 1,
            'turno': 'B',
            'linha_montagem': 'LM-02',
            'inspetor': 'Mariana Lima',
            'status': 'aprovado',
            'observacao': 'Produto aprovado sem restrições'
        },
        {
            'data_inspecao': date(2025, 12, 24),
            'semana': '52',
            'cod_sap': 'B91201922',
            'linha': 'Liquificador',
            'familia': 'Taurus',
            'modelo': 'Liquificador',
            'descricao_sap': 'Liquificador Taurus 220V',
            'qtd_total': 72,
            'qtd_inspecionada': 6,
            'qtd_nc': 2,
            'rastreabilidade': '255233HX',
            'po': 'PO-9874',
            'qtd_pallet': 1,
            'turno': 'C',
            'linha_montagem': 'LM-03',
            'inspetor': 'Ana Pereira',
            'status': 'reprovado',
            'observacao': 'Identificado problema na fiação',
            'documento': 'PANP-001',
            'defeito': 'Fiação inadequada',
            'prioridade': 'critico',
            'origem_problema': 'Problema originado na montagem da linha'
        }
    ]
    
    # Inserir registros
    for dados in registros_exemplo:
        registro = RegistroInspecao(**dados)
        db.session.add(registro)
    
    db.session.commit()
    print("✅ Dados de exemplo inseridos")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python migrate.py [init|migrate|upgrade|setup]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'init':
        init_db()
    elif command == 'migrate':
        message = sys.argv[2] if len(sys.argv) > 2 else "Auto migration"
        create_migration(message)
    elif command == 'upgrade':
        apply_migrations()
    elif command == 'setup':
        setup_database()
    else:
        print(f"Comando desconhecido: {command}")
        print("Comandos disponíveis: init, migrate, upgrade, setup")