#!/bin/bash
# Test script for timeout features

echo "Starting test..."
sleep 2
echo "Output after 2 seconds"
sleep 5
echo "Output after 7 seconds"
sleep 5
echo "Output after 12 seconds"
sleep 100
echo "This should not be reached with idle timeout"

