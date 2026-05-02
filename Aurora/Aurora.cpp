#include "dpp/appcommand.h"
#include "dpp/cluster.h"
#include "dpp/dispatcher.h"
#include "dpp/once.h"
#include <cstdlib>
#include <iostream>

#include <dpp/dpp.h>

int main (int argc, char* argv[])
{
    const char* envBotTokenName = "AURORA_TOKEN";
  
    const char* envBotTokenValue = std::getenv(envBotTokenName);

    if (envBotTokenValue == NULL)
    {
        std::cerr << "Token não encontrado. Impossível conectar." << std::endl;
        return 1;
    }

    dpp::cluster bot(envBotTokenValue);

    
    bot.on_log(dpp::utility::cout_logger());

    
    bot.on_slashcommand([](const dpp::slashcommand_t& event) {
        if (event.command.get_command_name() == "ping")
        {
            event.reply("Pong!");
        }
    });
    
    bot.on_ready([&bot](const dpp::ready_t& event) {
        if (dpp::run_once<struct registerBotCommands>())
          {
            bot.global_command_create(dpp::slashcommand("ping", "Ping, pong!", bot.me.id));
      
          }
    });

    
    bot.start(dpp::st_wait);
    //bot.start(false);
    

    std::cout << "Este é um teste do bot Aurora." << std::endl;
  

    return 0;
}
