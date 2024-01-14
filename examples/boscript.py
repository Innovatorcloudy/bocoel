from collections.abc import Sequence
from typing import Literal

import datasets
import fire
from rich import print
from tqdm import tqdm

from bocoel import (
    AcquisitionFunc,
    AxServiceOptimizer,
    BigBenchChoiceType,
    BigBenchMatchType,
    BigBenchMultipleChoice,
    BigBenchQuestionAnswer,
    ComposedCorpus,
    ConcatStorage,
    DatasetsStorage,
    Distance,
    HnswlibIndex,
    HuggingfaceLM,
    SBertEmbedder,
    WhiteningIndex,
)


def main(
    *,
    ds_path: str = "bigbench",
    ds_names: Sequence[str] | Literal["all"] = ("abstract_narrative_understanding",),
    ds_split: str = "default",
    inputs: str = "inputs",
    multiple_choice_targets: str = "multiple_choice_targets",
    multiple_choice_scores: str = "multiple_choice_scores",
    targets: str = "targets",
    sbert_model: str = "all-mpnet-base-v2",
    llm_model: str = "distilgpt2",
    batch_size: int = 16,
    max_len: int = 512,
    device: str = "cpu",
    sobol_steps: int = 20,
    index_threads: int = 8,
    optimizer_steps: int = 30,
    reduced_dim: int = 16,
    multiple_choice: bool,
    metric: str,
    acqf: str = "ENTROPY",
) -> None:
    # The corpus part
    if ds_names == "all":
        ds_names = _ALL_BIG_BENCH

    for dataset_id in ds_names:
        assert dataset_id in _ALL_BIG_BENCH

    dataset_list: list[DatasetsStorage] = []

    for dataset_to_load in ds_names:
        dataset_dict = datasets.load_dataset(path=ds_path, name=dataset_to_load)
        dataset = dataset_dict[ds_split]
        dataset_list.append(DatasetsStorage(dataset))

    storage = ConcatStorage.join(dataset_list)

    embedder = SBertEmbedder(model_name=sbert_model, device=device)
    corpus = ComposedCorpus.index_storage(
        storage=storage,
        embedder=embedder,
        key=inputs,
        index_backend=WhiteningIndex,
        distance=Distance.INNER_PRODUCT,
        remains=reduced_dim,
        whitening_backend=HnswlibIndex,
        threads=index_threads,
    )

    # ------------------------
    # The model part

    lm = HuggingfaceLM(
        model_path=llm_model, device=device, batch_size=batch_size, max_len=max_len
    )
    evaluator = get_evaluator(
        inputs=inputs,
        multiple_choice_targets=multiple_choice_targets,
        multiple_choice_scores=multiple_choice_scores,
        targets=targets,
        multiple_choice=multiple_choice,
        metric=metric,
    )

    # ------------------------
    # The optimizer part.

    optim = AxServiceOptimizer.evaluate_corpus(
        corpus=corpus,
        lm=lm,
        evaluator=evaluator,
        sobol_steps=sobol_steps,
        device=device,
        acqf=AcquisitionFunc.lookup(acqf),
    )

    for i in tqdm(range(optimizer_steps)):
        state = optim.step()
        print(f"iteration {i}:", state)


def get_evaluator(
    inputs: str,
    multiple_choice_targets: str,
    multiple_choice_scores: str,
    targets: str,
    multiple_choice: bool,
    metric: str,
) -> BigBenchMultipleChoice | BigBenchQuestionAnswer:
    if metric not in _ALLOWED_METRIC_KEYS:
        raise ValueError(f"Metric must be one of {_ALLOWED_METRIC_KEYS}, got {metric}.")

    if multiple_choice:
        return BigBenchMultipleChoice(
            inputs=inputs,
            multiple_choice_targets=multiple_choice_targets,
            multiple_choice_scores=multiple_choice_scores,
            choice_type=BigBenchChoiceType(metric),
        )
    else:
        return BigBenchQuestionAnswer(
            inputs=inputs,
            targets=targets,
            matching_type=BigBenchMatchType(metric),
        )


if __name__ == "__main__":
    fire.Fire(main)
_ALLOWED_METRIC_KEYS = [
    "exact",
    "nltk-bleu",
    "sacre-bleu",
    "rouge",
    "rouge-score-1",
    "rouge-score-2",
    "rouge-score-L",
    "one-hot",
    "multi-choice",
]
_ALL_BIG_BENCH = """
abstract_narrative_understanding anachronisms analogical_similarity analytic_entailment arithmetic ascii_word_recognition
authorship_verification auto_categorization auto_debugging bbq_lite_json bridging_anaphora_resolution_barqa causal_judgment
cause_and_effect checkmate_in_one chess_state_tracking chinese_remainder_theorem cifar10_classification code_line_description
codenames color common_morpheme conceptual_combinations conlang_translation contextual_parametric_knowledge_conflicts crash_blossom
crass_ai cryobiology_spanish cryptonite cs_algorithms dark_humor_detection date_understanding disambiguation_qa
discourse_marker_prediction disfl_qa dyck_languages elementary_math_qa emoji_movie emojis_emotion_prediction empirical_judgments
english_proverbs english_russian_proverbs entailed_polarity entailed_polarity_hindi epistemic_reasoning
evaluating_information_essentiality fact_checker fantasy_reasoning few_shot_nlg figure_of_speech_detection
formal_fallacies_syllogisms_negation gem gender_inclusive_sentences_german general_knowledge geometric_shapes goal_step_wikihow
gre_reading_comprehension hhh_alignment hindi_question_answering hindu_knowledge hinglish_toxicity human_organs_senses hyperbaton
identify_math_theorems identify_odd_metaphor implicatures implicit_relations intent_recognition international_phonetic_alphabet_nli
international_phonetic_alphabet_transliterate intersect_geometry irony_identification kanji_ascii kannada key_value_maps
known_unknowns language_games language_identification linguistic_mappings linguistics_puzzles list_functions logic_grid_puzzle
logical_args logical_deduction logical_fallacy_detection logical_sequence mathematical_induction matrixshapes metaphor_boolean
metaphor_understanding minute_mysteries_qa misconceptions misconceptions_russian mnist_ascii modified_arithmetic
moral_permissibility movie_dialog_same_or_different movie_recommendation mult_data_wrangling multiemo natural_instructions navigate
nonsense_words_grammar novel_concepts object_counting odd_one_out operators paragraph_segmentation parsinlu_qa
parsinlu_reading_comprehension penguins_in_a_table periodic_elements persian_idioms phrase_relatedness physical_intuition physics
physics_questions play_dialog_same_or_different polish_sequence_labeling presuppositions_as_nli qa_wikidata question_selection
real_or_fake_text reasoning_about_colored_objects repeat_copy_logic rephrase riddle_sense ruin_names
salient_translation_error_detection scientific_press_release semantic_parsing_in_context_sparc semantic_parsing_spider
sentence_ambiguity similarities_abstraction simp_turing_concept simple_arithmetic_json simple_arithmetic_json_multiple_choice
simple_arithmetic_json_subtasks simple_arithmetic_multiple_targets_json simple_ethical_questions simple_text_editing snarks
social_iqa social_support sports_understanding strange_stories strategyqa sufficient_information suicide_risk
swahili_english_proverbs swedish_to_german_proverbs symbol_interpretation temporal_sequences tense timedial topical_chat
tracking_shuffled_objects understanding_fables undo_permutation unit_conversion unit_interpretation unnatural_in_context_learning
vitaminc_fact_verification what_is_the_tao which_wiki_edit winowhy word_sorting word_unscrambling""".strip().split()