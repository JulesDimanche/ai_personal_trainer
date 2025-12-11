import json
import faiss
import numpy as np
from typing import List
from fastembed import TextEmbedding


FITNESS_KB = [
    "Plateaus happen when you repeat the same training load without progressive overload.",
    "Insufficient sleep reduces muscle recovery and performance.",
    "Being in a calorie deficit for too long can reduce strength and workout intensity.",
    "Incorrect exercise form limits muscle activation and slows progress.",
    "Low protein intake can delay muscle repair and hinder strength gains.",
    "Inconsistent training frequency is one of the biggest reasons for stalled progress.",
    "Long-term high stress increases cortisol, limiting recovery and impairing performance.",
    "Poorly balanced workouts can cause muscle imbalances and slow improvement.",
    "Lack of deload weeks can lead to accumulated fatigue and plateaus.",
    "Overestimating calorie burn can lead to accidental calorie surplus and fat gain.",
]


def build_vector_db(
    kb_items: List[str],
    json_output_path="fitness_kb.json",
    index_output_path="fitness_kb.index",
    embedding_model_name="BAAI/bge-small-en-v1.5"
):

    print("Loading lightweight embedding model...")
    model = TextEmbedding(embedding_model_name)

    print("Encoding KB...")
    embeddings = list(model.embed(kb_items))
    embeddings = np.array(embeddings, dtype="float32")   # Convert to numpy

    dimension = embeddings.shape[1]

    print("Creating FAISS index...")
    index = faiss.IndexFlatL2(dimension)

    print("Adding vectors...")
    index.add(embeddings)

    print(f"Total vectors stored: {index.ntotal}")

    faiss.write_index(index, index_output_path)
    print(f"Vector index saved to: {index_output_path}")

    kb_map = {i: kb_items[i] for i in range(len(kb_items))}
    with open(json_output_path, "w") as f:
        json.dump(kb_map, f, indent=4)
    print(f"KB mapping saved to: {json_output_path}")

    print("Vector DB creation complete.")


if __name__ == "__main__":
    build_vector_db(FITNESS_KB)
