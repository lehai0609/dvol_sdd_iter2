# API Contracts

This directory contains OpenAPI 3.0 specifications for all CryptoDataDownload API endpoints used in the DVOL data ingestion pipeline.

## Contract Files

1. **dvol_api_contract.json** - DVOL OHLC data endpoint
2. **options_api_contract.json** - Options summary and greeks endpoint
3. **futures_api_contract.json** - Futures OHLCV data endpoint
4. **funding_api_contract.json** - Funding rates endpoint
5. **onchain_api_contract.json** - On-chain blockchain data endpoint

## Usage

These contracts define:
- Request parameters and validation rules
- Response schemas and field types
- Error handling and status codes
- Example requests and responses

## Validation

Contract tests should validate:
- All required fields are present
- Field types match schema definitions
- Value ranges are within specified bounds
- Date formats are consistent (YYYY-MM-DD)
- Error responses match expected formats

## Schema Evolution

When API schemas change:
1. Update the relevant contract file
2. Increment the version number
3. Update corresponding Pydantic models
4. Run contract tests to verify compatibility
5. Document breaking changes in migration notes

## Testing Integration

Use these contracts with tools like:
- OpenAPI Generator for client code generation
- Swagger UI for interactive API documentation
- Contract testing frameworks (Pact, etc.)
- API mocking for development and testing