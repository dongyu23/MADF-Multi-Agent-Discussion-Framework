@echo off
echo Running Backend Tests with Coverage...
cd %~dp0
pytest app/tests --cov=app --cov-report=html:backend-coverage-report --cov-report=term-missing

echo Running Frontend Tests with Coverage...
cd frontend
npm run test:coverage

echo All tests completed. Reports are in backend-coverage-report and frontend/coverage.
pause
