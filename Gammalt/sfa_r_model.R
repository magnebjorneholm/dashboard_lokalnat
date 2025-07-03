# sfa_r_model.R

library(frontier)
library(openxlsx)

# Läs in
df <- read.xlsx("output/sfa_input.xlsx")

# Log-transformering
df$ln_OPEXp <- log(df$OPEXp)
df$ln_CAPEX <- log(df$CAPEX)
df$ln_MW    <- log(df$MW)
df$ln_NS    <- log(df$NS)
df$ln_MWhl  <- log(df$MWhl)

# Modell
model <- sfa(
  ln_MWhl ~ ln_OPEXp + ln_CAPEX + ln_MW + ln_NS,
  data = df,
  truncNorm = TRUE
)

# Ineffektivitet
u_hat <- efficiencies(model)
theta <- exp(-u_hat)

# Effektivitetskrav
revred <- 1 - theta
revred_compress <- pmin(pmax(revred, 0.162416), 0.3)
effkrav <- ((1 + revred_compress / 4)^0.25) - 1

# Lägg till
df$Effektivitet <- theta
df$Effkrav_proc <- effkrav

# Skriv resultat
write.xlsx(df[, c("DMU", "Företag", "CU", "MWhh", "NS", "MWhl", "Effektivitet", "Effkrav_proc")],
           "output/sfa_result.xlsx", overwrite = TRUE)

