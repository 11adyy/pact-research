"""
Example: Connecting Claude to pact-runtime
==========================================

This example shows how to wire Claude (via the Anthropic API) to execute
skills and capabilities through pact-runtime' embedded runtime.

No HTTP server needed — everything runs in-process.

Requirements:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...

Usage:
    python examples/claude_agent_example.py
"""

from __future__ import annotations

import json
import os


def main():
                                                                    
                                                    
                                                                    
    from sdk.embedded import as_anthropic_tools

                                                                   
    tools, dispatch = as_anthropic_tools([
        "text.content.summarize",
        "data.json.parse",
    ])

                                                           
     
         
           
                                             
                                                                    
                             
                               
                             
                                           
                                                 
                
                                  
             
            
             
         
     
                                                        
     
         
                                               
                                        
         

    print(f"Registered {len(tools)} tools for Claude:")
    for t in tools:
        print(f"  - {t['name']}: {t['description'][:60]}...")

                                                                    
                                  
                                                                    
    import anthropic

    client = anthropic.Anthropic()                                  

    messages = [
        {
            "role": "user",
            "content": (
                "Summarize the following text in one sentence:\n\n"
                "Machine learning is a subset of artificial intelligence that "
                "focuses on building systems that learn from data. Instead of "
                "being explicitly programmed, these systems improve their "
                "performance through experience. Applications range from image "
                "recognition to natural language processing and autonomous "
                "vehicles."
            ),
        }
    ]

    print("\n--- Sending to Claude ---")

                                                               
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

                                    
        tool_calls = []
        text_output = []

        for block in response.content:
            if block.type == "text":
                text_output.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(block)

                                                                
        if not tool_calls:
            print("\n--- Claude's response ---")
            print("\n".join(text_output))
            break

                                
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for call in tool_calls:
            print(f"\n  [Tool call] {call.name}({json.dumps(call.input, ensure_ascii=False)[:100]})")

                                                       
            result = dispatch[call.name](**call.input)

            print(f"  [Result]    {json.dumps(result, ensure_ascii=False)[:100]}")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "user", "content": tool_results})


                                                                
                                                         
                                                                

def minimal_example():
    """Simplest possible connection — no API call, just shows the plumbing."""
    from sdk.embedded import as_anthropic_tools

    tools, dispatch = as_anthropic_tools(["text.content.summarize"])

                                                                  
    print("Tool definition for Anthropic API:")
    print(json.dumps(tools, indent=2))

                                                                     
                                                                                    
    print("\nTo execute: dispatch['text_content_summarize'](text='...', max_length=20)")


if __name__ == "__main__":
    if os.environ.get("ANTHROPIC_API_KEY"):
        main()
    else:
        print("No ANTHROPIC_API_KEY set — running minimal example.\n")
        minimal_example()
