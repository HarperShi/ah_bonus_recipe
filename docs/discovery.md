# AH Bonus Scraper Discovery

Discovery run: `data/discovery/20260515T112740Z/report.md`

## Confirmed Endpoints

- `POST https://api.ah.nl/mobile-auth/v1/auth/token/anonymous`
  - Body: `{"clientId": "appie-ios"}`
  - Returns an anonymous bearer token.
- `GET https://api.ah.nl/mobile-services/bonuspage/v3/metadata`
  - Returns current and next Bonus periods plus category URLs.
- `GET https://api.ah.nl/mobile-services/bonuspage/v2/section?...`
  - Returns direct Bonus products and group cards for a category.
- `POST https://api.ah.nl/graphql`
  - `bonusPromotions` expands group cards into individual products.
- `GET https://api.ah.nl/mobile-services/product/detail/v4/fir/{webshop_id}`
  - Returns `productCard` plus `tradeItem` detail data.

## Required Headers

- `Authorization: Bearer <anonymous-token>`
- `x-client-name: appie-ios`
- `x-client-version: 9.28`
- `x-application: AHWEBSHOP`
- `user-agent: Appie/9.28 (...)`

## Useful Fields

- Weekly dates: `periods[].bonusStartDate`, `periods[].bonusEndDate`
- Product identity: `webshopId`, `hqId`, `title`, `brand`
- Promotion identity: `bonusSegmentId`, `bonusSegmentDescription`, `offerId`
- Prices: `priceBeforeBonus`, `currentPrice`, `discountLabels`
- Ingredients: `tradeItem.foodAndBeverageIngredientStatement`
- Allergens: `tradeItem.allergenInformation`
- Nutrition: `tradeItem.nutritionalInformation.nutrientHeaders`
- Portion/package: `salesUnitSize`, `tradeItem.measurements.netContent`, serving info

## Implementation Notes

The full weekly scraper should use metadata as the source of truth, iterate each `NATIONAL` section, expand each group whose `products` list is empty, fetch product detail for every unique product ID, and store both raw and normalized data.
