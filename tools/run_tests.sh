#!/bin/bash
# Quick test runner for collaboration server
# Run from the project root directory

echo "======================================================================"
echo "COLLABORATION SERVER TEST RUNNER"
echo "======================================================================"
echo ""
echo "This script will run the automated collaboration test."
echo "Make sure you've started the server first!"
echo ""
echo "To start server: python tools/collaboration_server_v2.py"
echo ""
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

echo ""
echo "Starting test..."
echo ""

python tools/test_collaboration.py

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================================================"
    echo "SUCCESS: All tests passed!"
    echo "======================================================================"
    echo ""
    echo "Next step: Test with Optiverse application"
    echo "  1. Start server: python tools/collaboration_server_v2.py"
    echo "  2. Launch Optiverse"
    echo "  3. View -> Show Log"
    echo "  4. File -> Collaboration -> Connect"
    echo "  5. Verify connection stays alive"
    echo ""
else
    echo ""
    echo "======================================================================"
    echo "FAILED: Tests did not pass"
    echo "======================================================================"
    echo ""
    echo "Check the output above for details."
    echo "Make sure the server is running:"
    echo "  python tools/collaboration_server_v2.py"
    echo ""
fi

