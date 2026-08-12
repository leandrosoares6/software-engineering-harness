# Task

No menu do WhatsApp, sessões cujo access token já expirou mas que ainda têm um
refresh_token válido estão sendo tratadas como deslogadas. O usuário é jogado no fluxo de
login em vez de ter a sessão renovada automaticamente.

## Provenance

- commit: `bebffa5`
- schema_version: `seh.context/v0.1`
- built_by: hand — na Fase 0 o seed é escolhido por um humano de propósito, para medir o teto

## Seeds

- `app/agent/nodes/orchestrator.py` — monta o menu e decide se a sessão está autenticada
- `app/agent/nodes/autoservice/whatsapp_flows.py` — handler do canal WhatsApp

## Target Symbols

### `create_orchestrator_node()`
- file: `app/agent/nodes/orchestrator.py:217`
- included because: explicit seed; contém os três pontos onde a autenticação é decidida

Três chamadas decidem "está autenticado?" sem tentar renovação:

<source>
app/agent/nodes/orchestrator.py:278    not state.auth.verify_authentication()
app/agent/nodes/orchestrator.py:684    is_authenticated = state.auth.verify_authentication()
app/agent/nodes/orchestrator.py:722    is_authenticated = state.auth.verify_authentication()
</source>

A de `:684` é a que monta o menu:

<source>
channel = state.conversation.channel
identifier = state.conversation.thread_id
is_authenticated = state.auth.verify_authentication()

# Filtrar serviços bloqueados considerando identifier (whitelist)
blocked_services = get_blocked_services_for_channel(channel, identifier=identifier)
</source>

### `WhatsAppFlowHandler.should_handle_whatsapp_flow(state)`
- file: `app/agent/nodes/autoservice/whatsapp_flows.py:34`
- included because: explicit seed; é onde `pending_federated_auth` é interpretado

<source>
# Aguardando autenticação federada
if state.auth.pending_federated_auth:
    # Se o callback já chegou e o usuário já está autenticado,
    # limpa o estado pendente e continua o fluxo normalmente.
    if state.auth.verify_authentication():
        logger.info("[WHATSAPP_FLOW] pending_federated_auth=True but user already authenticated — clearing stale state ...")
        clear_pending_auth_state(state)
        # Fall through para o restante do fluxo normal
</source>

## Related Symbols

### `AuthenticationData`
- file: `app/models/authentication.py:10`
- included because: 1-hop — é o tipo de `state.auth`, usado pelos dois seeds

<source>
class AuthenticationData(BaseModel):
    user_id: Optional[str] = None
    user_info: Optional[UserInfo] = None
    token: Optional[str] = None
    refresh_token: Optional[str] = None

    # Campos para gerenciar callback de autenticação federada
    pending_federated_auth: bool = False
    federated_auth_started_at: Optional[float] = None
    device_trust_preference: Optional[bool] = None
    ...

    def verify_authentication(self) -> bool:
        """Verifica se o usuário está autenticado."""
        if not self.token:
            return False
        valid = verify_jwt(self.token)
        if not valid:
            self.token = None  # Limpar token expirado/inválido
            return False
</source>

Nota: `verify_authentication()` olha **só** o `token`. Nunca consulta `refresh_token`.

### `auto_refresh_token_if_needed(state) -> bool`
- file: `app/agent/nodes/autoservice/flows/authentication.py:149`
- included because: 1-hop — já importado por `whatsapp_flows.py:10`; é a renovação que já existe

<summary>
Verifica e automaticamente renova o token se necessário (específico para WhatsApp).
A renovação só faz sentido para dispositivos confiáveis no WhatsApp, onde o usuário optou
por confiar no número para futuras sessões.
</summary>

Já é usado em `whatsapp_flows.py:114` (`is_authenticated = await auto_refresh_token_if_needed(state)`),
mas **não** nos três pontos do orquestrador acima.

### `clear_pending_auth_state(state)`
- file: importado em `app/agent/nodes/autoservice/whatsapp_flows.py:10`
- included because: 1-hop — já usado no bloco de `pending_federated_auth`

## Tests

- `tests/test_alo_cidadao.py` — `TestGlobalExitOrchestrator` cobre caminhos do orquestrador
- `tests/test_runtime_config.py` — `TestRuntimeConfig` cobre fluxo do WhatsApp

Suíte pré-existente: 450 passed.

## Unknowns

- Nenhum símbolo indexado para o termo "menu autenticado": a decisão de menu está inline em
  `create_orchestrator_node`, não num símbolo próprio.
