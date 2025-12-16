# /formularios/repositories/evolutionRepository.py

import requests
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class EvolutionRepository:
    """
    Camada de repositório para interagir com a Evolution API.
    Versão final alinhada com a documentação.
    """
    @staticmethod
    def _make_request(method: str, host: str, api_key: str, endpoint: str, timeout: int = 60, **kwargs) -> Dict[str, Any]:
        """Função centralizada para realizar todas as requisições HTTP."""
        url = f"{host.rstrip('/')}/{endpoint}"
        headers = {"apikey": api_key, "Content-Type": "application/json"}
        try:
            # Passa 'params' para requisições GET e 'json' para POST/PUT etc.
            response = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
            response.raise_for_status()
            if response.status_code in [200, 204] and not response.content:
                return {"status": "success", "message": "Operação realizada com sucesso."}
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            try:
                error_details = http_err.response.json()
                error_message = f"Erro da API: {error_details}"
            except json.JSONDecodeError:
                error_message = f"Erro HTTP: {http_err.response.status_code} - {http_err.response.text}"
            logger.error(f"Erro na chamada para '{url}': {error_message}")
            return {"status": "error", "message": error_message}
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Erro de conexão com '{url}': {req_err}")
            return {"status": "error", "message": "Erro de conexão com a API."}

    # --- Métodos de Gerenciamento da Instância ---
    def criar_instancia(host: str, api_key: str, instance_name: str) -> Dict[str, Any]:
        """Cria uma nova instância ou obtém o status de uma existente."""
        # CORREÇÃO: Adicionado o parâmetro 'integration'
        payload = {
            "instanceName": instance_name, 
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS"
        }
        return EvolutionRepository._make_request("POST", host, api_key, "instance/create", json=payload)
    @staticmethod
    def get_status(host: str, api_key: str, instance_name: str) -> Dict[str, Any]:
        """Verifica o status da conexão de uma instância."""
        return EvolutionRepository._make_request("GET", host, api_key, f"instance/connectionState/{instance_name}")

    @staticmethod
    def get_qrcode(host: str, api_key: str, instance_name: str) -> Dict[str, Any]:
        """Obtém o QR Code para conectar uma instância já criada."""
        return EvolutionRepository._make_request("GET", host, api_key, f"instance/connect/{instance_name}")

    @staticmethod
    def desconectar(host: str, api_key: str, instance_name: str) -> Dict[str, Any]:
        """Desconecta (logout) uma instância do WhatsApp."""
        return EvolutionRepository._make_request("DELETE", host, api_key, f"instance/logout/{instance_name}")

    @staticmethod
    def reiniciar(host: str, api_key: str, instance_name: str) -> Dict[str, Any]:
        """Reinicia o serviço de uma instância."""
        return EvolutionRepository._make_request("POST", host, api_key, f"instance/restart/{instance_name}")


    # --- Métodos de Envio de Mensagens ---
    @staticmethod
    def enviar_mensagem_texto(host: str, api_key: str, instance_name: str, number: str, text: str) -> Dict[str, Any]:
        """Envia uma mensagem de texto simples."""
        payload = {"number": number, "text": text}
        return EvolutionRepository._make_request("POST", host, api_key, f"message/sendText/{instance_name}", json=payload)

  
    @staticmethod
    def enviar_midia(host: str, api_key: str, instance_name: str, number: str, mediatype: str, mimetype: str, media_data: str, caption: str, file_name: str) -> Dict[str, Any]:
        """Envia uma mídia (imagem, vídeo, doc) a partir de uma string Base64."""
        payload = {
            "number": number,
            "mediatype": mediatype,
            "mimetype": mimetype,
            "caption": caption,
            "media": media_data, # Espera a string Base64 pura
            "fileName": file_name
        }
        return EvolutionRepository._make_request("POST", host, api_key, f"message/sendMedia/{instance_name}", json=payload)

    @staticmethod
    def enviar_audio(host: str, api_key: str, instance_name: str, number: str, audio_data: str) -> Dict[str, Any]:
        """Envia um áudio (PTT) a partir de uma string Base64."""
        payload = {"number": number, "audio": audio_data} # Espera a string Base64 pura
        return EvolutionRepository._make_request("POST", host, api_key, f"message/sendWhatsAppAudio/{instance_name}", json=payload)

    @staticmethod
    def enviar_mensagem_com_botao(host: str, api_key: str, instance_name: str, number: str, text: str, button_text: str, button_url: str) -> Dict[str, Any]:
        """
        Envia uma mensagem com link formatado.
        
        IMPORTANTE: Evolution API v2 com Baileys NÃO suporta sendButtons.
        Erro da API: "Method not available on WhatsApp Baileys"
        
        Solução: Enviar mensagem de texto formatada com link clicável.
        O WhatsApp detecta automaticamente URLs e as torna clicáveis.
        """
        # Formata a mensagem com link clicável e emojis para destaque visual
        mensagem_formatada = f"""📩 *Mensagem Importante*

{text}

🔗 *{button_text}*
👉 {button_url}

_Clique no link acima para acessar_"""
        
        # Usa o endpoint de texto simples que funciona 100% no Baileys
        payload = {"number": number, "text": mensagem_formatada}
        return EvolutionRepository._make_request("POST", host, api_key, f"message/sendText/{instance_name}", json=payload)

 # --- NOVAS FUNÇÕES PARA GRUPOS ---
    @staticmethod
    def get_todos_grupos(host: str, api_key: str, instance_name: str, get_participants: bool = False) -> Dict[str, Any]:
        """
        Busca todos os grupos dos quais a instância participa.
        
        Args:
            get_participants (bool): Se True, inclui os participantes de cada grupo na resposta.
                                     Isso é mais eficiente do que chamar get_participantes_grupo separadamente.
        """
        endpoint = f"group/fetchAllGroups/{instance_name}"
        # ### ALTERAÇÃO AQUI ###
        # Adiciona o parâmetro 'getParticipants' na chamada da API
        params = {"getParticipants": str(get_participants).lower()}
        return EvolutionRepository._make_request("GET", host, api_key, endpoint, params=params)

    @staticmethod
    def get_participantes_grupo(host: str, api_key: str, instance_name: str, group_id: str) -> Dict[str, Any]:
        """Busca os participantes de um grupo específico usando o endpoint GET."""
        # Esta função continua aqui, mas não será mais usada pela tarefa de exportação.
        endpoint = f"group/participants/{instance_name}"
        params = {"groupJid": group_id}
        return EvolutionRepository._make_request("GET", host, api_key, endpoint, params=params)

