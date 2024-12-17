from monocle_apptrace.instrumentation.metamodel.langchain import (
  _helper,
)

INFERENCE = {
  "type": "inference",
  "attributes": [
    [
      {
        "_comment": "provider type ,name , deployment , inference_endpoint",
        "attribute": "type",
        "accessor": lambda arguments:'inference.azure_oai'
      },
      {
        "attribute": "provider_name",
        "accessor": lambda arguments:_helper.extract_provider_name(arguments['instance'])
      },
      {
        "attribute": "deployment",
        "accessor": lambda arguments: _helper.resolve_from_alias(arguments['instance'].__dict__, ['engine', 'azure_deployment', 'deployment_name', 'deployment_id', 'deployment'])
      },
      {
        "attribute": "inference_endpoint",
        "accessor": lambda arguments: _helper.resolve_from_alias(arguments['instance'].__dict__, ['azure_endpoint', 'api_base', 'endpoint']) or _helper.extract_inference_endpoint(arguments['instance'])
      }
    ],
    [
      {
        "_comment": "LLM Model",
        "attribute": "name",
        "accessor": lambda arguments: _helper.resolve_from_alias(arguments['instance'].__dict__, ['model', 'model_name'])
      },
      {
        "attribute": "type",
        "accessor": lambda arguments: 'model.llm.'+_helper.resolve_from_alias(arguments['instance'].__dict__, ['model', 'model_name'])
      }
    ]
  ],
  "events": [
    { "name":"data.input",
      "attributes": [

          {
              "_comment": "this is instruction and user query to LLM",
              "attribute": "input",
              "accessor": lambda arguments: _helper.extract_messages(arguments['args'])
          }
      ]
    },
    {
      "name":"data.output",
      "attributes": [
        {
            "_comment": "this is result from LLM",
            "attribute": "response",
            "accessor": lambda arguments: _helper.extract_assistant_message(arguments['result'])
        }
      ]
   }
  ]
}