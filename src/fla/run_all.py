from . import pipeline, stats, model, alerts, dashboard
if __name__ == "__main__":
    pipeline.run(); stats.run(); model.run(); alerts.run(); dashboard.run()
