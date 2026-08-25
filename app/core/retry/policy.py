class RetryPolicy:

    @property
    def max_attempt(self) -> int:
        ...
    
    def should_retry(
            self,
            exception: Exception,
            attempt: int,
    ) -> bool:
        ...

    def next_delay(
            self,
            attempt: int,
    ) -> float:
        ...