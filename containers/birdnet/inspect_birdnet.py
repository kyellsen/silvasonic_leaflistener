
import sys
import inspect

output_file = "inspection_result.txt"

with open(output_file, "w") as f:
    try:
        import birdnet_analyzer.analyze as bn_analyze
        f.write("Imported successfully.\n")
        f.write(f"Type of bn_analyze: {type(bn_analyze)}\n")

        if inspect.ismodule(bn_analyze):
            f.write("It is a module. Contents:\n")
            f.write(str(dir(bn_analyze)) + "\n")
            if hasattr(bn_analyze, 'analyze'):
                func = bn_analyze.analyze
                f.write(f"Signature of analyze: {inspect.signature(func)}\n")
                f.write(f"Source file: {inspect.getfile(func)}\n")
            else:
                f.write("Module has no 'analyze' attribute.\n")
        elif callable(bn_analyze):
             f.write(f"It is a callable. Signature: {inspect.signature(bn_analyze)}\n")
             f.write(f"Source file: {inspect.getfile(bn_analyze)}\n")
        else:
             f.write(f"It is neither module nor simple callable: {bn_analyze}\n")

    except Exception as e:
        f.write(f"Error: {e}\n")
