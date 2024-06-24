execute_process(
  COMMAND "${CTESTEXAMPLE_COMMAND}"
  RESULT_VARIABLE CTESTEXAMPLE_RESULT
  OUTPUT_VARIABLE CTESTEXAMPLE_OUTPUT
)

if(NOT CTESTEXAMPLE_RESULT EQUAL "0")
  message(FATAL_ERROR "ctestexample returned non-zero value\nActual result: ${CTESTEXAMPLE_RESULT}")
endif()

if(NOT CTESTEXAMPLE_OUTPUT STREQUAL "Hello world!\n")
  message(FATAL_ERROR "ctestexample did not print \"Hello world!\"\nActual result:\n${CTESTEXAMPLE_OUTPUT}")
endif()
