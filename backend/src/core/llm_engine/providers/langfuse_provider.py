"""
Langfuse LLM provider implementation
"""
import asyncio
from openai import OpenAI
from langfuse import Langfuse
from .base import LLMProvider


class LangfuseProvider(LLMProvider):
    """Langfuse provider for LLM interactions with observability"""
    
    def __init__(self, public_key: str, secret_key: str, host: str, model: str = "anthropic.claude-sonnet-4-20250514-v1", **kwargs):
        if not public_key or not secret_key or not host:
            raise ValueError("Langfuse public_key, secret_key, and host are required")
        
        # Initialize Langfuse client
        self.langfuse = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host
        )
        
        # Create OpenAI client that uses Langfuse as base URL
        # Langfuse expects API key in format: sk-<secret_key>:pk-<public_key>
        combined_api_key = f"{secret_key}:{public_key}"
        self.client = OpenAI(
            api_key=combined_api_key,
            base_url=host
        )
        
        self.model = model
        self.max_tokens = kwargs.get('max_tokens', 2000)
        self.temperature = kwargs.get('temperature', 0.1)
        self.timeout = kwargs.get('timeout', 30)
        
        # Store configuration for debugging
        self.config = {
            'public_key': public_key[:10] + "...",  # Truncated for security
            'host': host,
            'model': model,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'timeout': self.timeout
        }
    
    async def generate_diagnosis(self, prompt: str) -> str:
        """Generate diagnosis using Langfuse with OpenAI client and observability tracking"""
        
        # Create a trace for this diagnosis request
        trace = self.langfuse.trace(
            name="log_diagnosis",
            metadata={
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }
        )
        
        try:
            # Create a generation within the trace
            generation = trace.generation(
                name="diagnosis_generation",
                model=self.model,
                input=prompt,
                metadata={
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "timeout": self.timeout
                }
            )
            
            # Make the API call using OpenAI client with Langfuse base URL
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert software engineer and DevOps specialist. Your job is to analyze error logs and provide detailed diagnosis including root cause analysis and recommendations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout=self.timeout
            )
            
            # Extract the response content
            content = response.choices[0].message.content.strip()
            
            # Update the generation with the response
            generation.end(
                output=content,
                usage={
                    "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "output_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                }
            )
            
            # End the trace successfully
            trace.update(
                output={"diagnosis_length": len(content)},
                metadata={"status": "success"}
            )
            
            return content
                
        except Exception as e:
            # Log the error in the trace
            generation.end(
                level="ERROR",
                status_message=str(e)
            )
            trace.update(
                metadata={"status": "error", "error": str(e)}
            )
            raise RuntimeError(f"Langfuse API error: {e}")
        finally:
            # Ensure the trace is flushed
            self.langfuse.flush()
