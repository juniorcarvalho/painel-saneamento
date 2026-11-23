from langchain_core.language_models.fake_chat_models import GenericFakeChatModel


class FakeToolChatModel(GenericFakeChatModel):
    """Fake chat model com suporte a tool calling (bind_tools retorna self)."""

    def bind_tools(self, tools, **kwargs):
        return self
