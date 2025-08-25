# 📝 Sistema de Controle de Fiado

[![Status](https://img.shields.io/badge/status-em%20produção-blue)](#️-deployment)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.x-orange)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL-blue)](https://www.postgresql.org/)
[![Deployment](https://img.shields.io/badge/Deployed%20on-Render.com-black)](https://render.com/)

Sistema web completo para gerenciar "fiado" (dívidas) de clientes. Desenvolvido com Python e Flask, o projeto permite cadastrar clientes, registrar itens de dívida e pagamentos, com acesso administrativo protegido por login.


## 📋 Índice

-   [Sobre o Projeto](#-sobre-o-projeto)
-   [✨ Funcionalidades Principais](#-funcionalidades-principais)
-   [🚀 Stack de Tecnologia](#-stack-de-tecnologia)
-   [🛡️ Segurança](#️-segurança)
-   [👨‍💻 Autor](#-autor)

## 📖 Sobre o Projeto

Este projeto é uma ferramenta leve e eficiente para pequenos comerciantes controlarem as dívidas de seus clientes. É uma aplicação CRUD (Create, Read, Update, Delete) completa, desenvolvida com Flask. A arquitetura é flexível, permitindo rodar em um ambiente de desenvolvimento local com um banco de dados PostgreSQL e em um ambiente de produção na nuvem sem alterações no código.

## ✨ Funcionalidades Principais

-   **Dashboard Central**: Visualização rápida do total devido, total de clientes e total de pagamentos.
-   **Gerenciamento de Clientes**: CRUD completo para clientes (criar, listar, editar e excluir).
-   **Controle de Fiados**: Registro de itens de dívida por cliente, com descrição e valor.
-   **Registro de Pagamentos**: Sistema para registrar pagamentos parciais ou totais, que abate automaticamente os fiados mais antigos.
-   **Autenticação Segura**: Sistema de login com `Flask-Login`, senhas com hash e rotas protegidas.
-   **Backup de Dados**: Funcionalidade para exportar todos os dados do sistema em formato JSON.

## 🚀 Stack de Tecnologia

-   **Backend**: Python, Flask, Flask-Login, Flask-SQLAlchemy
-   **Banco de Dados**: PostgreSQL (utilizando Supabase para produção)
-   **Frontend**: HTML5, CSS3, Jinja2
-   **Hospedagem**: Render.com
-   **Bibliotecas**: `python-dotenv`, `werkzeug.security`

## 🛡️ Segurança

A aplicação foi desenvolvida com foco em segurança, seguindo as melhores práticas:

-   **Variáveis de Ambiente**: Nenhuma credencial (chaves de banco de dados, `SECRET_KEY`) está exposta no código-fonte. Todas as chaves são carregadas a partir de variáveis de ambiente.
-   **Hash de Senhas**: As senhas dos usuários são armazenadas no banco de dados usando o hash `pbkdf2:sha256`, garantindo que mesmo em caso de vazamento do banco, as senhas não sejam expostas.
-   **Proteção de Rotas**: O acesso a todas as páginas de gerenciamento é protegido e requer autenticação.

