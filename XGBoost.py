import pandas as pd
import numpy as np
from sklearn.model_selection import RandomizedSearchCV
from sklearn.metrics import mean_squared_error, r2_score,mean_absolute_percentage_error
import xgboost as xgb
import warnings
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore')

# Load data from CSV
file_path = r'Bulkcsv24.csv'
df = pd.read_csv(file_path)



# Create forecast error column and lag features
df['forecast_error'] = df['FORECASTDEMAND'] - df['TOTALDEMAND']

# Add weekend flag and interaction with hour
df['IsWeekend'] = df['Day of week'].isin([5, 6]).astype(int)  # Saturday=5, Sunday=6
df['Hour_IsWeekend'] = df['Hour'] * df['IsWeekend']

# # Create rolling average features
# df['rolling_12h'] = df['TOTALDEMAND'].shift(24).rolling(window=24).mean()
# df['rolling_24h'] = df['TOTALDEMAND'].shift(24).rolling(window=48).mean()
# df['rolling_48h'] = df['TOTALDEMAND'].shift(24).rolling(window=96).mean()

# df['rolling_forecast_error_12h'] = df['forecast_error'].shift(24).rolling(window=24).mean()
# df['rolling_forecast_error_24h'] = df['forecast_error'].shift(24).rolling(window=48).mean()
# df['rolling_forecast_error_48h'] = df['forecast_error'].shift(24).rolling(window=96).mean()



# Sort by datetime for splitting to be time based
df = df.sort_values('DATETIME')

features = ['temperature', 'humidity', 'wind_speed', 'rain', 'Hour', 'FORECASTDEMAND',
            '24hrpreverror','48hrpreverror', 'Hour_IsWeekend', 
            #'lag_12h', 'lag_24h', 'lag_48h',
            #'rolling_12h', 'rolling_24h', 'rolling_48h',
            #'rolling_forecast_error_12h','rolling_forecast_error_24h','rolling_forecast_error_48h'
            ]


X = df[features]
y = df['TOTALDEMAND']
forecast = df['FORECASTDEMAND']
total = df['TOTALDEMAND']

# Split using previous time metric
split_index = int(len(df) * 0.7)
train_df = df.iloc[:split_index]
test_df = df.iloc[split_index:]
X_train = train_df[features]
y_train = train_df['TOTALDEMAND']
X_test = test_df[features]
y_test = test_df['TOTALDEMAND']

# Parameter grid used for fine-tuning
param_dist = {
    'n_estimators': [100, 150, 200, 250,300,400,350,450],
    'learning_rate': [0.05, 0.1, 0.2, 0.3,0.02,0.15,0.07],
    'max_depth': [4, 5, 6, 7,3,8],
    'subsample': [0.6, 0.8, 1.0],
    'colsample_bytree': [0.8, 1.0],
    'gamma': [0, 0.1, 0.3],
    'reg_alpha': [0, 0.1, 0.5, 1],
    'reg_lambda': [1, 2, 3]
}

# # Initialise XGBoost model
# base_model = xgb.XGBRegressor(objective='reg:squarederror', random_state=42)

# # Fine-tune using above parameter grid
# random_search = RandomizedSearchCV(
#     estimator=base_model,
#     param_distributions=param_dist,
#     n_iter=50,
#     scoring='neg_mean_squared_error',
#     cv=5,
#     verbose=1,
#     random_state=42,
#     n_jobs=-1
# )

# # Fit the model
# random_search.fit(X_train, y_train)
# model = random_search.best_estimator_

#OUTPUT OF ABOVE
#{'subsample': 0.8, 'reg_lambda': 1, 'reg_alpha': 1, 'n_estimators': 400, 'max_depth': 3, 'learning_rate': 0.07, 'gamma': 0.3, 'colsample_bytree': 0.8}

# Train XGBoost model with fixed parameters
model = xgb.XGBRegressor(
    objective='reg:squarederror',
    subsample=0.8,
    reg_lambda=1,
    reg_alpha=1,
    n_estimators=400,
    max_depth=3,
    learning_rate=0.07,
    gamma=0.3,
    colsample_bytree=0.8,
    random_state=42
)

model.fit(X_train, y_train)


# Predict and evaluate
y_pred = model.predict(X_test)
forecast_test = X_test['FORECASTDEMAND']

# Generate metrics
mse_model = mean_squared_error(y_test, y_pred)
r2_model = r2_score(y_test, y_pred)
mse_forecast = mean_squared_error(total, forecast)
r2_forecast = r2_score(total, forecast)



mape_model = mean_absolute_percentage_error(y_test, y_pred) * 100
mape_forecast = mean_absolute_percentage_error(total, forecast) * 100

# Evaluate how close predictions are to actual demand
percent_error_model = np.abs(y_pred - y_test) / y_test * 100
percent_error_forecast = np.abs(forecast_test - y_test) / y_test * 100

thresholds = [1, 3, 5, 10, 25, 50]

# # Output
# print("\n Best Parameters Found:")
# print(random_search.best_params_)

print("\n XGBoost Model Performance:")
print(f"MSE Model: {mse_model:.2f}")
print(f"MSE Forecast: {mse_forecast:.2f}")
print(f"R² Model: {r2_model:.4f}")
print(f"R² Forecast: {r2_forecast:.4f}")
print(f"MAPE Model: {mape_model:.4f}%")
print(f"MAPE ForecastDemand: {mape_forecast:.4f}%")
print("\nPrediction Accuracy within Error Thresholds (Model):")
for t in thresholds:
    count = np.sum(percent_error_model <= t)
    pct = count / len(y_test) * 100
    print(f"Within ±{t}%: {count} predictions ({pct:.2f}%)")

print("\nForecastDemand Accuracy within Error Thresholds:")
for t in thresholds:
    count = np.sum(percent_error_forecast <= t)
    pct = count / len(y_test) * 100
    print(f"Within ±{t}%: {count} predictions ({pct:.2f}%)")

# Calculate percentage errors
percent_error_model = np.abs(y_pred - y_test) / y_test * 100
percent_error_forecast = np.abs(forecast_test - y_test) / y_test * 100

thresholds = [1, 2, 3, 5, 10, 15]
summary_data = []

for t in thresholds:
    model_count = np.sum(percent_error_model <= t)
    forecast_count = np.sum(percent_error_forecast <= t)
    total = len(y_test)
    model_pct = model_count / total * 100
    forecast_pct = forecast_count / total * 100
    summary_data.append([f"±{t}%", model_count, f"{model_pct:.2f}%", forecast_count, f"{forecast_pct:.2f}%"])

summary_df = pd.DataFrame(summary_data, columns=[
    "Threshold", "Model Count", "Model %", "Forecast Count", "Forecast %"
])

# Display the table
print("\n📋 Summary Table:")
print(summary_df.to_string(index=False))

# Plotting
x_labels = [f"±{t}%" for t in thresholds]
model_values = [np.sum(percent_error_model <= t) / len(y_test) * 100 for t in thresholds]
forecast_values = [np.sum(percent_error_forecast <= t) / len(y_test) * 100 for t in thresholds]


# # Convert to arrays for plotting
y_test_array = np.array(y_test)
y_pred_array = np.array(y_pred)
residuals = y_test_array - y_pred_array

# Plot 1: Actual vs Predicted
plt.figure(figsize=(10, 6))
plt.scatter(y_test_array, y_pred_array, alpha=0.5)
plt.plot([y_test_array.min(), y_test_array.max()], [y_test_array.min(), y_test_array.max()], 'r--', lw=2)
plt.title("Actual vs Predicted TotalDemand (XGBoost Model)")
plt.xlabel("Actual TotalDemand")
plt.ylabel("Predicted TotalDemand")
plt.grid(True)
plt.tight_layout()
plt.show()

# Plot 2: Residuals vs Fitted Values
plt.figure(figsize=(10, 6))
plt.scatter(y_pred_array, residuals, alpha=0.5)
plt.axhline(y=0, color='r', linestyle='--')
plt.title("Residuals vs Predicted Values")
plt.xlabel("Predicted TotalDemand")
plt.ylabel("Residuals")
plt.grid(True)
plt.tight_layout()
plt.show()
