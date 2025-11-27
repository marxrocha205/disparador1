# Implementação de Botões com Links - Guia de Deploy

## Alterações Implementadas

### 1. Modelo (models.py)
- ✅ Adicionado campo `incluir_botao` (BooleanField)
- ✅ Adicionado campo `botao_texto` (CharField, max 100 caracteres)
- ✅ Adicionado campo `botao_url` (URLField, max 500 caracteres)

### 2. Formulário (forms.py)
- ✅ Adicionados campos de formulário com validação
- ✅ Validação: se `incluir_botao=True`, botao_texto e botao_url são obrigatórios
- ✅ Interface Tailwind CSS estilizada

### 3. Repositório Evolution API (evolutionRepository.py)
- ✅ Nova função `enviar_mensagem_com_botao()` 
- ✅ Endpoint: POST /message/sendButtons/{instance_name}
- ✅ Formato de botão URL compatível com Evolution API v2.1.1

### 4. Tasks Celery (tasks.py)
- ✅ Nova task `enviar_notificacao_whatsapp_botao()`
- ✅ Modificado `verificar_disparos()` para detectar e usar botões quando configurado
- ✅ Mantém compatibilidade com envios de texto simples

### 5. Template (formulario.html)
- ✅ Seção de botão com checkbox "Incluir Botão com Link"
- ✅ Campos ocultos que aparecem quando checkbox marcado
- ✅ JavaScript para controlar visibilidade dos campos
- ✅ Estilo visual destacado (fundo azul claro)

### 6. Migração do Banco
- ✅ Arquivo de migração criado: `0024_mensagem_botao_fields.py`

## Como Fazer Deploy no Railway

### Opção 1: Deploy Automático (Recomendado)
```bash
# 1. Commit e push das alterações
git add .
git commit -m "feat: adicionar funcionalidade de botões com links"
git push origin master

# O Railway vai automaticamente:
# - Fazer rebuild do serviço django-web
# - Executar as migrations no start.sh
# - Reiniciar celery-worker e celery-beat
```

### Opção 2: Deploy Manual Local
```bash
# 1. Fazer backup do banco (opcional mas recomendado)
# No Railway, na aba do PostgreSQL (django)

# 2. Aplicar migrations localmente para teste
python manage.py makemigrations
python manage.py migrate

# 3. Testar localmente com docker-compose
docker-compose up --build

# 4. Push para Railway
git add .
git commit -m "feat: adicionar funcionalidade de botões com links"
git push origin master
```

## Como Usar a Nova Funcionalidade

### 1. No Formulário de Mensagem
1. Preencha os campos normais (destinatários, mensagem, etc)
2. Marque o checkbox "Incluir Botão com Link"
3. Preencha:
   - **Texto do Botão**: Ex: "Acesse Nossa Página"
   - **URL do Botão**: Ex: "https://seusite.com"
4. Agende normalmente

### 2. Formato do Botão WhatsApp
A mensagem será enviada com:
```
[Sua mensagem de texto aqui]

┌───────────────────┐
│ 🔗 Acesse Nossa Página │  ← Botão clicável
└───────────────────┘
```

### 3. Exemplo de Payload Evolution API
```json
{
  "number": "+5511988887777",
  "message": "Olá! Confira nossa promoção especial",
  "buttons": [
    {
      "type": "url",
      "displayText": "Ver Promoção",
      "url": "https://suaempresa.com/promo"
    }
  ]
}
```

## Verificação Pós-Deploy

### 1. Verificar Migrations
```bash
# No Railway, logs do serviço django-web:
# Deve aparecer:
# Running migrations:
#   Applying formulario_professores.0024_mensagem_botao_fields... OK
```

### 2. Testar no Admin Django
1. Acesse https://django-web-production-b4e9.up.railway.app/admin
2. Vá em "Mensagens"
3. Edite uma mensagem existente
4. Verifique se aparecem os novos campos:
   - ☑️ Incluir Botão com Link
   - Texto do Botão
   - URL do Botão

### 3. Testar Envio Real
1. Crie uma nova mensagem
2. Marque "Incluir Botão com Link"
3. Preencha os dados do botão
4. Agende para o minuto seguinte
5. Verifique no WhatsApp:
   - Mensagem deve chegar com botão clicável
   - Ao clicar, deve abrir a URL no navegador

## Troubleshooting

### ❌ Erro: "buttons" não reconhecido
**Problema**: Evolution API não aceita o campo buttons
**Solução**: Verifique a versão da Evolution API
```bash
# Deve ser v2.1.1 ou superior
# No docker-compose.yml da Evolution:
image: atendai/evolution-api:v2.1.1
```

### ❌ Botão não aparece no WhatsApp
**Problema**: Algumas versões antigas do WhatsApp não suportam botões
**Solução**: 
- Peça ao destinatário atualizar WhatsApp
- Use CONFIG_SESSION_PHONE_VERSION=2.3000.1030400153

### ❌ Migration não aplicada
**Problema**: Banco não tem os novos campos
**Solução**:
```bash
# Conecte ao Railway e execute manualmente:
python manage.py migrate formulario_professores 0024
```

### ❌ Campos não aparecem no formulário
**Problema**: Template cache ou JavaScript não carregou
**Solução**:
1. Limpe o cache do navegador (Ctrl+Shift+Del)
2. Force reload (Ctrl+F5)
3. Verifique console do navegador (F12)

## Limitações Conhecidas

1. **Máximo 3 botões por mensagem** (Evolution API v2)
2. **Botões URL não funcionam em grupos** (limitação WhatsApp)
3. **Texto do botão: máximo 20-25 caracteres** (recomendação WhatsApp)
4. **URL deve ser HTTPS** (segurança WhatsApp)

## Próximos Passos (Opcional)

- [ ] Adicionar suporte para múltiplos botões (até 3)
- [ ] Adicionar botões de resposta rápida (reply buttons)
- [ ] Adicionar listas interativas (list messages)
- [ ] Dashboard para análise de cliques em botões
- [ ] Webhooks para capturar respostas

## Commit para Railway

```bash
git add .
git commit -m "feat: implementar botões com links nas mensagens WhatsApp

- Adicionar campos incluir_botao, botao_texto, botao_url no modelo Mensagem
- Criar task enviar_notificacao_whatsapp_botao()
- Atualizar repositório Evolution API com endpoint sendButtons
- Interface de formulário com checkbox e campos condicionais
- Migração 0024_mensagem_botao_fields.py
- Validação de campos obrigatórios quando botão habilitado
- Suporte completo para Evolution API v2.1.1"

git push origin master
```

## Status: ✅ PRONTO PARA DEPLOY
