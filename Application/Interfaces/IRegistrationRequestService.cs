using Application.DTOs;
using Domain.Entities;
using System;
using System.Collections.Generic;
using System.Linq.Expressions;
using System.Text;

namespace Application.Interfaces
{
    public interface IRegistrationRequestService
    {
        Task<RegistrationRequestDto?> GetByIdAsync(int id);
        Task<IEnumerable<RegistrationRequestDto>> GetAllAsync();
        Task CreateAsync(RegistrationRequestDto request);
        //Task UpdateAsync(RegistrationRequestDto request);
        Task DeleteAsync(int id);
    }
}

