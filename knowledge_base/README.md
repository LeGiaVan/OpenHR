# Interview criteria knowledge base

This folder is the editable source for industry, job-family, role, competency,
question, rubric, and source metadata. Add content as YAML and validate it
against the JSON Schemas in the schemas folder.

## Content model

- taxonomies: broad industry and job-family identifiers.
- roles/<industry>/<role>/: role-specific competencies, questions, and rubrics.
- sources/manifest.yaml: provenance and review status for authored/imported material.
- schemas: machine-readable shape checks for knowledge-base records.

Interview-level behavior and timer policies live separately in the configs folder.
The workflow combines CV/JD context with relevant retrieved records. Do not store
candidate CVs or interview transcripts here.

## Adding a role

1. Add or reuse an industry and job-family ID in taxonomies.
2. Copy the starter files from roles/_template/ into roles/<industry>/<role>/.
3. Add competencies and evidence cues expected at intern/fresher level.
4. Add question templates with type, difficulty, competency IDs, and follow-up
   intent. Questions are prompts for the interviewer, not a fixed script.
5. Add a rubric with observable score anchors and register content sources.
6. Validate and review the content before enabling it for retrieval.

Keep IDs stable, record sources, and prefer observable evidence over vague traits.
A role may inherit shared competencies from its job family and add specific ones.

These starter files define structure; they are not a complete, validated interview dataset.
