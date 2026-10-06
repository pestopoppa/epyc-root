# Typed candidate descriptions: non-inference preparation

Question carries optional immutable position-aligned descriptions. JSON and native catalogues bind them to original option labels even when opaque answer keys differ; native layout and JSON readers preserve their original order. Empty defaults preserve legacy prompt/layout bytes. Strict shape/arity/single-line validation rejects ambiguous or malformed inputs. Candidate labels, schema, keys, probabilities and return values retain existing authority.

Descriptions are optional display metadata for CHOICE questions only. An empty tuple keeps the old form; a populated sequence must align one-for-one with options, may contain None, and rejects blank/multiline text and unordered/text outer containers. No live caller is enabled.

[Original native evidence](../../artifacts/ni07/run-37468262427/README.md) passes14/14 exact selected synthetic cases, excluding later real wire-stack tests. Original37466999348 remains FALSE13/14: two test assertions incorrectly reordered descriptions by answer-key interpretation. MAIN reviewed the original-option order and approved only those two expectations. The original receipt/JUnit/ZIP is unchanged. Parent TD-14 retains the TD-16 described-versus-undescribed no-harm comparison; no quality/adoption or inference claim.
