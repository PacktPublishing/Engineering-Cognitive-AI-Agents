# Chapter 4: Knowledge Management

This chapter implements a sophisticated Knowledge Management System (KMS) for Winston, our AI assistant. The KMS enhances Winston's ability to store, retrieve, and reason over information, making it a more capable and context-aware conversational agent.

## Key Features

1. **Multi-tiered Knowledge Storage**: Utilizes file storage, SQLite database, and ChromaDB for efficient information management.

2. **Content Ingestion**: Extracts entities, relationships, and attributes from unstructured text to create a knowledge graph.

3. **Advanced Querying**: Implements QA retrieval, knowledge graph-based recall, and Retrieval-Augmented Generation (RAG) for comprehensive information retrieval.

4. **Dynamic Knowledge Updates**: Allows for the ingestion and integration of new information through the 'remember' intent.

5. **Confidence-based Responses**: Implements a system for calculating and expressing confidence in responses.

## Main Components

- `QAIndex` class in `qa_index.py`: Implements a QA retrieval system using ChromaDB.
- `GraphDB` class in `graph_db.py`: Manages the knowledge graph using SQLite.
- `KnowledgeManagementSystem` class in `kms.py`: Handles core KMS functionalities.
- `winston_knows.py`: Integrates KMS with Winston's conversational abilities.
- New intent handlers: Implements 'remember' and 'question' intents for knowledge interaction.
- Several new prompt templates.

## Usage

Ensure all required environment variables are set and necessary prompt templates are available. Run Winston as a Chainlit application to interact with the enhanced knowledge-driven AI assistant.

For detailed implementation, refer to the following files:

- `kms.py`
- `graph_db.py`
- `qa_index.py`
- `winston_knows.py`

### Prompt Templates

- `prompts/ch04/intent/classifier/help.md`
- `prompts/ch04/intent/help.md`
- `prompts/ch04/intent/question.md`
- `prompts/ch04/intent/remember_confirm.md`
- `prompts/ch04/intent/remember_extract.md`
- `prompts/ch04/knowledge/extract_attributes.md`
- `prompts/ch04/knowledge/extract_entities.md`
- `prompts/ch04/knowledge/extract_relationships.md`
- `prompts/ch04/knowledge/qa_pairs_json.md`
- `prompts/ch04/knowledge/qa_paris.md`
- `prompts/ch04/knowledge/reword_question.md`
