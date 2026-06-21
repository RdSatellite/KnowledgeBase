import os

from langchain_openai.embeddings import OpenAIEmbeddings

from ..abc import BaseEmbedFunction

class TextEmbedFunction(BaseEmbedFunction):
    def __init__(self):
        self._model = "text-embedding-3-small"
        self._dim = 1536
        self._client = OpenAIEmbeddings(
            model = self._model,
            api_key=os.environ.get("API_KEY"),
            base_url=os.environ.get("BASE_URL")
        )

    @property
    def model(self) -> str:
        """Embedding model name (e.g. ``'text-embedding-3-small'``)"""
        return self._model

    @property
    def dim(self) -> int:
        """Dimensionality of the vectors produced by this model"""
        return self._dim

    # --- Helpers --- #
    def _validate_input(self, texts: list[str]) -> None:
        """
        Make sure the texts in really list[str], not single str, not empty, etc.
        Prevent DB pollution. (Python will iter str and create useless embeddings silently)
        """
        if type(texts) is not list:
            raise TypeError(
                "texts must be list[str]. "
                "Passing str directly is forbidden. "
            )

        if not texts:
            raise ValueError("texts is empty")
        
        for i, text in enumerate(texts):
            if type(text) is not str:
                raise TypeError(
                    f"texts[{i}] is not str."
                )

            if not text.strip():
                raise ValueError(
                    f"texts[{i}] is empty."
                )

    def _validate_output(self, texts: list[str], embeddings: list[list[float]]) -> None:
        """
        Make sure every text is correctly embed
        If not, they shouldn't be inserted into DB
        """
        if len(embeddings) != len(texts):
            raise RuntimeError(
                "Embedding result count mismatch."
            )
    
        for i, embed in enumerate(embeddings):
            if len(embed) != self.dim:
                raise RuntimeError(
                    f"Embedding dimension mismatch at index {i}: "
                    f"expected {self.dim}, got {len(embed)}"
                )

    # --- Embedding --- #

    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Convert *texts* into embedding vectors

        :param texts:  one or more text strings to embed
        :returns:      embedding vectors in the same order as *texts*;
                       each vector has length :attr:`dim`
        """
        self._validate_input(texts)
        embeddings = self._client.embed_documents(texts)
        self._validate_output(texts, embeddings)

        return embeddings
