from rag.intent_classifier import classify_intent
from rag.retrieval import retrieve_properties
from rag.rag_response import generate_rag_response


def run_query(user_query: str) -> str:
    """
    End-to-end execution following strict RAG order:
    Intent → Retrieval → Explanation → LLM
    """

    # STEP 1: Intent Classification (MANDATORY FIRST)
    intent = classify_intent(user_query)

    # STEP 2: Deterministic Retrieval (NO LLM)
    retrieved_df = retrieve_properties(intent, user_query)

    # STEP 3: RAG Explanation (LLM allowed here only)
    response = generate_rag_response(
        user_query=user_query,
        intent=intent,
        retrieved_df=retrieved_df,
    )

    return response


if __name__ == "__main__":
    # Simple manual test (LLM response is placeholder)
    question = "Why is 4 BHK Villa for Sale in Arizuma Southern Vista, Rajpur Sonarpur Kolkata marked as BUY?"
    print(run_query(question))
